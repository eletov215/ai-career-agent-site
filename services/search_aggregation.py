"""Stable bounded multi-provider pagination for SEARCH-003.

The service materializes a short-lived anonymous snapshot in PostgreSQL/SQLite.
It never stores query text in observability and never scans an entire provider
corpus synchronously. Canonical filtering and SEARCH-002 deduplication happen
before stable ordinals are assigned.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence

from repositories import SearchSnapshotRepository

from .base_provider import SearchResult
from .search_filters import VacancySearchFilters, filter_vacancies
from .vacancy_deduplication import deduplicate_vacancies
from .vacancy_normalizer import clean_text, normalize_datetime

logger = logging.getLogger(__name__)

SEARCH_PIPELINE_VERSION = 1
_SOURCE_PRIORITY = {
    "hh": 10,
    "superjob": 20,
    "trudvsem": 30,
    "reed": 40,
}


@dataclass(frozen=True, slots=True)
class SearchSourceSummary:
    """UI-facing provider state without raw errors or credentials."""

    source: str
    total: int
    loaded: int
    fetched_pages: int
    exhausted: bool
    bounded: bool
    has_next: bool
    error: str | None = None

    @property
    def fetched_items(self) -> int:
        """Compatibility name used by route telemetry."""

        return self.loaded


@dataclass(frozen=True, slots=True)
class SearchPage:
    """Stable logical page returned to the Flask route."""

    snapshot: Any
    snapshot_id: str
    page: int
    page_size: int
    items: list[dict[str, Any]]
    has_next: bool
    provider_reported_total: int
    known_unique_total: int
    total_is_exact: bool
    bounded: bool
    source_results: dict[str, SearchSourceSummary]
    errors: list[str]
    deduplication_stats: dict[str, int]
    snapshot_age_seconds: int
    committed_count: int
    late_arrival_count: int
    created: bool = False
    replaced: bool = False
    snapshot_restarted: bool = False


@dataclass(frozen=True, slots=True)
class _Materialized:
    rows: list[dict[str, Any]]
    dedup_stats: dict[str, int]
    late_arrival_count: int


ProviderFetcher = Callable[[str, int], SearchResult]


def search_query_fingerprint(
    filters: VacancySearchFilters,
    selected_sources: Sequence[str],
    *,
    page_size: int,
) -> str:
    """Return a stable query fingerprint without persisting raw parameters."""

    payload = {
        "pipeline_version": SEARCH_PIPELINE_VERSION,
        "filters": asdict(filters),
        "sources": sorted({str(source).strip() for source in selected_sources}),
        "page_size": max(1, int(page_size)),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _candidate_identity(item: Mapping[str, Any], source: str, index: int) -> str:
    """Return a stable per-provider publication identity.

    Provider IDs or URLs are preferred. The fallback includes provider page and
    position so two anonymous rows on different pages cannot overwrite each
    other inside the same persistent snapshot.
    """

    external_id = clean_text(item.get("external_id") or item.get("id"))
    url = clean_text(item.get("url"))
    title = clean_text(item.get("title"))
    company = clean_text(item.get("company"))
    provider_page = int(item.get("_snapshot_provider_page") or 0)
    provider_position = int(item.get("_snapshot_provider_position") or index)
    stable = external_id or url or (
        f"{title}:{company}:page={provider_page}:position={provider_position}"
    )
    return hashlib.sha256(f"{source}:{stable}".encode("utf-8")).hexdigest()[:40]


def _source_keys(item: Mapping[str, Any]) -> tuple[str, ...]:
    records = item.get("source_records")
    keys: list[str] = []
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, Mapping):
                continue
            source = clean_text(record.get("source")).casefold()
            external_id = clean_text(record.get("external_id"))
            url = clean_text(record.get("url"))
            stable = external_id or url
            if source and stable:
                keys.append(f"{source}:{stable}")
    if not keys:
        source = clean_text(item.get("source")).casefold() or "unknown"
        external_id = clean_text(item.get("external_id") or item.get("id"))
        url = clean_text(item.get("url"))
        stable = external_id or url
        if stable:
            keys.append(f"{source}:{stable}")
    if not keys:
        source = (
            clean_text(item.get("_snapshot_source") or item.get("source")).casefold()
            or "unknown"
        )
        provider_page = int(item.get("_snapshot_provider_page") or 0)
        provider_position = int(item.get("_snapshot_provider_position") or 0)
        fallback = "|".join(
            (
                source,
                clean_text(item.get("title")).casefold(),
                clean_text(item.get("company")).casefold(),
                clean_text(item.get("location")).casefold(),
                str(provider_page),
                str(provider_position),
            )
        )
        digest = hashlib.sha256(fallback.encode("utf-8")).hexdigest()[:32]
        keys.append(f"{source}:anonymous:{digest}")
    return tuple(sorted(set(keys)))


def _stable_key(source_keys: Iterable[str]) -> str:
    joined = "|".join(sorted(set(source_keys)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:40]


def _timestamp(value: Any) -> float:
    normalized = normalize_datetime(value)
    if not normalized:
        return 0.0
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _salary_value(
    item: Mapping[str, Any],
    *,
    descending: bool,
) -> tuple[bool, float]:
    fields = ("salary_to", "salary_from") if descending else ("salary_from", "salary_to")
    for field in fields:
        value = item.get(field)
        try:
            if value is not None:
                return False, float(value)
        except (TypeError, ValueError):
            continue
    return True, 0.0


def deterministic_sort_key(
    item: Mapping[str, Any],
    sort_code: str,
    keyword: str = "",
) -> tuple[Any, ...]:
    """Build an order independent of provider future-completion order.

    ``keyword`` is accepted for a stable public test/API signature but is not
    persisted or logged. Provider relevance scores are not comparable, so the
    relevance mode uses the deterministic provider page rank as a bounded
    approximation.
    """

    del keyword
    published = _timestamp(item.get("published_at"))
    title = clean_text(item.get("title")).casefold()
    company = clean_text(item.get("company")).casefold()
    source = clean_text(item.get("source")).casefold()
    external_id = clean_text(item.get("external_id") or item.get("id"))
    source_priority = _SOURCE_PRIORITY.get(source, 100)
    provider_rank = int(item.get("_snapshot_rank") or 0)

    tie_breaker = (
        title,
        company,
        source_priority,
        source,
        external_id,
        _stable_key(_source_keys(item)),
    )
    if sort_code == "salary_desc":
        missing, salary = _salary_value(item, descending=True)
        return (int(missing), -salary, -published, *tie_breaker)
    if sort_code == "salary_asc":
        missing, salary = _salary_value(item, descending=False)
        return (int(missing), salary, -published, *tie_breaker)
    if sort_code == "relevance":
        return (provider_rank, -published, *tie_breaker)
    return (-published, *tie_breaker)


def _decode_payload(value: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


class SearchAggregationService:
    """Create and incrementally extend stable bounded search snapshots."""

    def __init__(
        self,
        repository: SearchSnapshotRepository,
        *,
        page_size: int,
        ttl_seconds: int = 1800,
        max_pages_per_source: int = 8,
        max_candidates: int = 2000,
        max_rounds_per_request: int = 3,
        buffer_items: int = 1,
        extension_lease_seconds: int = 90,
    ) -> None:
        self.repository = repository
        self.page_size = max(1, min(int(page_size), 100))
        self.ttl_seconds = max(60, int(ttl_seconds))
        self.max_pages_per_source = max(1, min(int(max_pages_per_source), 100))
        self.max_candidates = max(self.page_size, int(max_candidates))
        self.max_rounds_per_request = max(1, min(int(max_rounds_per_request), 20))
        self.buffer_items = max(1, min(int(buffer_items), self.page_size))
        self.extension_lease_seconds = max(10, int(extension_lease_seconds))

    @staticmethod
    def _selected_sources_json(sources: Sequence[str]) -> str:
        return json.dumps(list(sources), ensure_ascii=False, separators=(",", ":"))

    def _valid_snapshot(
        self,
        snapshot_id: str | None,
        *,
        fingerprint: str,
        selected_sources: Sequence[str],
        sort_code: str,
    ):
        if not snapshot_id:
            return None
        snapshot = self.repository.get(snapshot_id)
        if snapshot is None:
            return None
        if (
            snapshot.query_fingerprint != fingerprint
            or snapshot.selected_sources_json
            != self._selected_sources_json(selected_sources)
            or snapshot.sort_code != sort_code
            or snapshot.page_size != self.page_size
        ):
            return None
        return snapshot

    def _new_snapshot(
        self,
        *,
        fingerprint: str,
        selected_sources: Sequence[str],
        sort_code: str,
    ):
        return self.repository.create(
            query_fingerprint=fingerprint,
            selected_sources=selected_sources,
            sort_code=sort_code,
            page_size=self.page_size,
            ttl_seconds=self.ttl_seconds,
        )

    @staticmethod
    def _source_map(records) -> dict[str, Any]:  # noqa: ANN001
        return {record.source: record for record in records}

    def _candidate_payloads(self, snapshot_id: str) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for candidate in self.repository.candidates(snapshot_id):
            payload = _decode_payload(candidate.payload_json)
            if payload is not None:
                payloads.append(payload)
        return payloads

    def _materialize(
        self,
        snapshot_id: str,
        *,
        sort_code: str,
        previous_committed_count: int,
        previous_late_arrivals: int,
    ) -> _Materialized:
        candidates = self._candidate_payloads(snapshot_id)
        dedup = deduplicate_vacancies(candidates)
        sorted_cards = sorted(
            dedup.items,
            key=lambda item: deterministic_sort_key(item, sort_code),
        )

        previous: list[dict[str, Any]] = []
        for row in self.repository.items(snapshot_id):
            payload = _decode_payload(row.payload_json)
            if payload is None:
                continue
            try:
                source_keys = tuple(str(value) for value in json.loads(row.source_keys_json))
            except (TypeError, json.JSONDecodeError):
                source_keys = _source_keys(payload)
            previous.append(
                {
                    "stable_key": row.stable_key,
                    "source_keys": source_keys,
                    "payload": payload,
                    "sort_key": deterministic_sort_key(payload, sort_code),
                    "ordinal": row.ordinal,
                }
            )
        previous.sort(key=lambda item: int(item["ordinal"]))
        committed_prefix = previous[: max(0, min(previous_committed_count, len(previous)))]

        identity_to_committed: dict[str, int] = {}
        for index, row in enumerate(committed_prefix):
            for key in row["source_keys"]:
                identity_to_committed[key] = index

        committed_updates: dict[int, dict[str, Any]] = {}
        tail_cards: list[dict[str, Any]] = []
        for card in sorted_cards:
            keys = _source_keys(card)
            matched_indexes = {
                identity_to_committed[key]
                for key in keys
                if key in identity_to_committed
            }
            if matched_indexes:
                index = min(matched_indexes)
                if len(matched_indexes) > 1:
                    logger.warning(
                        "Search snapshot merge touched multiple committed ordinals count=%s",
                        len(matched_indexes),
                        extra={
                            "event": "search_snapshot_multi_committed_match",
                            "match_count": len(matched_indexes),
                        },
                    )
                old = committed_prefix[index]
                committed_updates[index] = {
                    "stable_key": old["stable_key"],
                    "source_keys": keys,
                    "payload": card,
                    "sort_key": deterministic_sort_key(card, sort_code),
                    "ordinal": index,
                }
            else:
                tail_cards.append(
                    {
                        "stable_key": _stable_key(keys),
                        "source_keys": keys,
                        "payload": card,
                        "sort_key": deterministic_sort_key(card, sort_code),
                    }
                )

        for index, update in committed_updates.items():
            committed_prefix[index] = update

        # Once a page has been served, its committed prefix must never move.
        # Provider pages are expected to be monotonic for the requested sort;
        # any late item that would sort before the committed boundary is kept in
        # the uncommitted tail and counted for diagnostics instead of shifting a
        # page that the user already saw.
        tail_cards.sort(key=lambda item: item["sort_key"])
        late_arrival_count = previous_late_arrivals
        if committed_prefix and tail_cards:
            committed_boundary = committed_prefix[-1]["sort_key"]
            previous_source_keys = {
                key
                for row in previous
                for key in row["source_keys"]
            }
            late_arrival_count += sum(
                1
                for item in tail_cards
                if item["sort_key"] < committed_boundary
                and not previous_source_keys.intersection(item["source_keys"])
            )

        rows = committed_prefix + tail_cards
        for ordinal, row in enumerate(rows):
            row["ordinal"] = ordinal
        return _Materialized(
            rows=rows,
            dedup_stats=dedup.stats.as_dict(),
            late_arrival_count=late_arrival_count,
        )

    def _persist_materialization(
        self,
        snapshot_id: str,
        *,
        materialized: _Materialized,
        requested_commit_count: int,
        source_states: Mapping[str, Any],
    ):
        provider_total = sum(
            max(0, int(state.reported_total)) for state in source_states.values()
        )
        candidate_count = self.repository.candidate_count(snapshot_id)
        any_error = any(state.last_error_type for state in source_states.values())
        all_exhausted = bool(source_states) and all(
            state.exhausted for state in source_states.values()
        )
        # Reaching the numeric candidate ceiling is a real bound only while at
        # least one provider still has unread pages. A naturally exhausted set
        # whose size happens to equal the ceiling can still have an exact total.
        candidate_limit_reached = (
            candidate_count >= self.max_candidates and not all_exhausted
        )
        bounded = (
            any(state.bounded for state in source_states.values())
            or candidate_limit_reached
        )
        total_is_exact = all_exhausted and not bounded and not any_error
        rows = [
            {
                "stable_key": row["stable_key"],
                "source_keys": row["source_keys"],
                "payload": row["payload"],
            }
            for row in materialized.rows
        ]
        snapshot = self.repository.get(snapshot_id, include_expired=True)
        if snapshot is None:
            raise LookupError("Search snapshot not found")
        committed_count = min(
            max(snapshot.committed_count, requested_commit_count),
            len(rows),
        )
        return self.repository.replace_items(
            snapshot_id,
            items=rows,
            provider_reported_total=provider_total,
            candidate_count=materialized.dedup_stats["input_count"],
            duplicate_count=materialized.dedup_stats["duplicate_count"],
            cross_source_duplicate_count=materialized.dedup_stats[
                "cross_source_duplicate_count"
            ],
            cross_source_groups=materialized.dedup_stats["cross_source_groups"],
            total_is_exact=total_is_exact,
            bounded=bounded,
            committed_count=committed_count,
            late_arrival_count=materialized.late_arrival_count,
        )

    def _fetch_sources(
        self,
        snapshot_id: str,
        *,
        filters: VacancySearchFilters,
        fetch_page: ProviderFetcher,
        source_states: Mapping[str, Any],
        sources: Sequence[str],
    ) -> tuple[dict[str, Any], set[str]]:
        failed: set[str] = set()
        results: dict[str, SearchResult] = {}
        if not sources:
            return dict(source_states), failed

        with ThreadPoolExecutor(max_workers=min(len(sources), 4) or 1) as executor:
            futures = {
                executor.submit(fetch_page, source, source_states[source].next_page): source
                for source in sources
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    results[source] = future.result()
                except Exception as exc:  # Provider internals are already logged.
                    logger.exception("Snapshot provider fetch failed source=%s", source)
                    failed.add(source)
                    self.repository.record_source_error(
                        snapshot_id,
                        source=source,
                        error_type=type(exc).__name__,
                    )

        # Process completed futures in a fixed source order so persistence does
        # not depend on network completion order.
        for source in sorted(results):
            result = results[source]
            if result.error:
                failed.add(source)
                self.repository.record_source_error(
                    snapshot_id,
                    source=source,
                    error_type="ProviderSearchError",
                )
                continue
            provider_page = source_states[source].next_page
            normalized = filter_vacancies(result.items, filters)
            candidate_rows: list[tuple[str, dict[str, Any]]] = []
            for index, item in enumerate(normalized):
                payload = dict(item)
                payload["_snapshot_source"] = source
                payload["_snapshot_provider_page"] = provider_page
                payload["_snapshot_provider_position"] = index
                payload["_snapshot_rank"] = provider_page * 1000 + index
                candidate_rows.append(
                    (
                        _candidate_identity(payload, source, index),
                        payload,
                    )
                )
            self.repository.upsert_candidates(
                snapshot_id,
                source=source,
                provider_page=provider_page,
                candidates=candidate_rows,
            )
            max_pages_reached = (
                source_states[source].fetched_pages + 1 >= self.max_pages_per_source
            )
            self.repository.record_source_success(
                snapshot_id,
                source=source,
                provider_page=provider_page,
                reported_total=result.total,
                has_next=result.has_next,
                accepted_items=len(candidate_rows),
                max_pages_reached=max_pages_reached,
            )
        return self._source_map(self.repository.sources(snapshot_id)), failed

    def _extension_needed(
        self,
        snapshot_id: str,
        *,
        required_count: int,
        buffered_count: int,
        source_states: Mapping[str, Any],
    ) -> bool:
        """Return whether another bounded provider round is required.

        Aggregate cardinality alone is not sufficient for global ordering. For
        example, 60 candidates from Reed cannot prove the first global page is
        stable when HeadHunter has yielded only its first 20 rows. Before a
        page boundary is committed, every non-terminal provider must expose at
        least ``required_count`` accepted identities (or become exhausted /
        bounded). This is the per-provider coverage invariant that keeps unseen
        provider pages from silently outranking a served page.
        """

        snapshot = self.repository.get(snapshot_id, include_expired=True)
        if snapshot is None or snapshot.bounded:
            return False

        counts = self.repository.candidate_counts_by_source(snapshot_id)
        coverage_incomplete = any(
            not state.exhausted
            and not state.bounded
            and counts.get(source, 0) < required_count
            for source, state in source_states.items()
        )
        if coverage_incomplete:
            return True

        if snapshot.known_unique_total < buffered_count:
            return any(
                not state.exhausted and not state.bounded
                for state in source_states.values()
            )
        return False

    def _sources_to_fetch(
        self,
        snapshot_id: str,
        *,
        required_count: int,
        buffered_count: int,
        source_states: Mapping[str, Any],
        failed_this_request: set[str],
    ) -> list[str]:
        """Choose only providers needed for page coverage or a one-item tail."""

        counts = self.repository.candidate_counts_by_source(snapshot_id)
        eligible = [
            source
            for source, state in sorted(source_states.items())
            if not state.exhausted
            and not state.bounded
            and source not in failed_this_request
            and state.fetched_pages < self.max_pages_per_source
        ]
        coverage = [
            source for source in eligible if counts.get(source, 0) < required_count
        ]
        if coverage:
            return coverage

        snapshot = self.repository.get(snapshot_id, include_expired=True)
        if snapshot is not None and snapshot.known_unique_total < buffered_count:
            return eligible
        return []

    def search(
        self,
        *,
        filters: VacancySearchFilters,
        selected_sources: Sequence[str],
        page: int,
        snapshot_id: str | None,
        fetch_source: ProviderFetcher | None = None,
        fetch_page: ProviderFetcher | None = None,
    ) -> SearchPage:
        safe_page = max(0, int(page))
        sources = tuple(
            sorted(
                {
                    str(source).strip()
                    for source in selected_sources
                    if str(source).strip()
                }
            )
        )
        if not sources:
            sources = ("trudvsem",)
        fetcher = fetch_source or fetch_page
        if fetcher is None:
            raise TypeError("fetch_source is required")
        fingerprint = search_query_fingerprint(
            filters,
            sources,
            page_size=self.page_size,
        )

        self.repository.cleanup_expired(limit=50)
        valid = self._valid_snapshot(
            snapshot_id,
            fingerprint=fingerprint,
            selected_sources=sources,
            sort_code=filters.sort,
        )
        created = valid is None
        replaced = bool(snapshot_id and valid is None)
        if valid is None and safe_page > 0:
            # A page ordinal has meaning only inside a valid snapshot.
            safe_page = 0
        snapshot = valid or self._new_snapshot(
            fingerprint=fingerprint,
            selected_sources=sources,
            sort_code=filters.sort,
        )
        self.repository.touch(snapshot.id, ttl_seconds=self.ttl_seconds)

        required_count = (safe_page + 1) * self.page_size
        buffered_count = required_count + self.buffer_items
        source_states = self._source_map(self.repository.sources(snapshot.id))
        failed_this_request: set[str] = set()

        claimed = self.repository.try_claim_extension(
            snapshot.id,
            lease_seconds=self.extension_lease_seconds,
        )
        try:
            if claimed:
                # Repair or rebuild the materialized tail after a process
                # restart, but do not commit a new page boundary until the
                # bounded extension loop has gathered as much data as allowed.
                materialized = self._materialize(
                    snapshot.id,
                    sort_code=filters.sort,
                    previous_committed_count=snapshot.committed_count,
                    previous_late_arrivals=snapshot.late_arrival_count,
                )
                snapshot = self._persist_materialization(
                    snapshot.id,
                    materialized=materialized,
                    requested_commit_count=snapshot.committed_count,
                    source_states=source_states,
                )

                rounds = 0
                while (
                    self._extension_needed(
                        snapshot.id,
                        required_count=required_count,
                        buffered_count=buffered_count,
                        source_states=source_states,
                    )
                    and self.repository.candidate_count(snapshot.id)
                    < self.max_candidates
                    and rounds < self.max_rounds_per_request
                ):
                    fetch_sources = self._sources_to_fetch(
                        snapshot.id,
                        required_count=required_count,
                        buffered_count=buffered_count,
                        source_states=source_states,
                        failed_this_request=failed_this_request,
                    )
                    if not fetch_sources:
                        break
                    before_candidates = self.repository.candidate_count(snapshot.id)
                    source_states, failures = self._fetch_sources(
                        snapshot.id,
                        filters=filters,
                        fetch_page=fetcher,
                        source_states=source_states,
                        sources=fetch_sources,
                    )
                    failed_this_request.update(failures)
                    materialized = self._materialize(
                        snapshot.id,
                        sort_code=filters.sort,
                        previous_committed_count=snapshot.committed_count,
                        previous_late_arrivals=snapshot.late_arrival_count,
                    )
                    snapshot = self._persist_materialization(
                        snapshot.id,
                        materialized=materialized,
                        requested_commit_count=snapshot.committed_count,
                        source_states=source_states,
                    )
                    rounds += 1
                    after_candidates = self.repository.candidate_count(snapshot.id)
                    if after_candidates <= before_candidates and failures:
                        break

                # Commit only the requested page boundary. Any small buffered
                # tail remains movable until a later page is actually served.
                materialized = self._materialize(
                    snapshot.id,
                    sort_code=filters.sort,
                    previous_committed_count=snapshot.committed_count,
                    previous_late_arrivals=snapshot.late_arrival_count,
                )
                snapshot = self._persist_materialization(
                    snapshot.id,
                    materialized=materialized,
                    requested_commit_count=required_count,
                    source_states=source_states,
                )
            else:
                # Another request is extending this snapshot. Reuse the latest
                # committed state rather than issuing duplicate provider calls.
                time.sleep(0.05)
                snapshot = self.repository.get(snapshot.id) or snapshot
        finally:
            if claimed:
                self.repository.release_extension(
                    snapshot.id,
                    ttl_seconds=self.ttl_seconds,
                )

        snapshot = self.repository.get(snapshot.id) or snapshot
        source_states = self._source_map(self.repository.sources(snapshot.id))
        page_rows = self.repository.page_items(
            snapshot.id,
            page=safe_page,
            page_size=self.page_size,
        )
        page_items = [
            payload
            for row in page_rows
            if (payload := _decode_payload(row.payload_json)) is not None
        ]
        has_more_materialized = snapshot.known_unique_total > required_count
        can_extend = (not snapshot.bounded) and any(
            not state.exhausted for state in source_states.values()
        )
        has_next = has_more_materialized or can_extend

        source_results: dict[str, SearchSourceSummary] = {}
        errors: list[str] = []
        for source in sources:
            state = source_states[source]
            error = None
            if state.last_error_type:
                error = f"{source}: unavailable"
                errors.append(error)
            source_results[source] = SearchSourceSummary(
                source=source,
                total=state.reported_total,
                loaded=state.fetched_items,
                fetched_pages=state.fetched_pages,
                exhausted=state.exhausted,
                bounded=state.bounded,
                has_next=(not state.exhausted and not state.bounded),
                error=error,
            )

        dedup_stats = {
            "input_count": snapshot.candidate_count,
            "output_count": snapshot.known_unique_total,
            "duplicate_count": snapshot.duplicate_count,
            "identity_duplicate_count": max(
                0,
                snapshot.duplicate_count - snapshot.cross_source_duplicate_count,
            ),
            "cross_source_duplicate_count": snapshot.cross_source_duplicate_count,
            "cross_source_groups": snapshot.cross_source_groups,
            "exact_groups": 0,
            "similarity_groups": 0,
        }
        return SearchPage(
            snapshot=snapshot,
            snapshot_id=snapshot.id,
            page=safe_page,
            page_size=self.page_size,
            items=page_items,
            has_next=has_next,
            provider_reported_total=snapshot.provider_reported_total,
            known_unique_total=snapshot.known_unique_total,
            total_is_exact=snapshot.total_is_exact,
            bounded=snapshot.bounded,
            source_results=source_results,
            errors=errors,
            deduplication_stats=dedup_stats,
            snapshot_age_seconds=max(0, int(time.time()) - snapshot.created_at),
            committed_count=snapshot.committed_count,
            late_arrival_count=snapshot.late_arrival_count,
            created=created,
            replaced=replaced,
            snapshot_restarted=replaced,
        )


# Backward-compatible internal alias. New code should use search_query_fingerprint.
query_fingerprint = search_query_fingerprint
