"""Persistence contract for bounded SEARCH-003 result snapshots."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import delete, func, insert, or_, select, update

from domain import (
    SearchSnapshotCandidateRecord,
    SearchSnapshotItemRecord,
    SearchSnapshotRecord,
    SearchSnapshotSourceRecord,
)
from models import (
    SearchSnapshot,
    SearchSnapshotCandidate,
    SearchSnapshotItem,
    SearchSnapshotSource,
)

from .base import RepositoryBase


class SearchSnapshotRepository(RepositoryBase):
    """Store short-lived anonymous result snapshots outside vacancy cache data."""

    @staticmethod
    def _snapshot_record(row: SearchSnapshot) -> SearchSnapshotRecord:
        return SearchSnapshotRecord(
            id=row.id,
            query_fingerprint=row.query_fingerprint,
            selected_sources_json=row.selected_sources_json,
            sort_code=row.sort_code,
            page_size=row.page_size,
            status=row.status,
            provider_reported_total=row.provider_reported_total,
            known_unique_total=row.known_unique_total,
            committed_count=row.committed_count,
            late_arrival_count=row.late_arrival_count,
            candidate_count=row.candidate_count,
            duplicate_count=row.duplicate_count,
            cross_source_duplicate_count=row.cross_source_duplicate_count,
            cross_source_groups=row.cross_source_groups,
            total_is_exact=row.total_is_exact,
            bounded=row.bounded,
            extension_lease_until=row.extension_lease_until,
            created_at=row.created_at,
            updated_at=row.updated_at,
            expires_at=row.expires_at,
        )

    @staticmethod
    def _source_record(row: SearchSnapshotSource) -> SearchSnapshotSourceRecord:
        return SearchSnapshotSourceRecord(
            source=row.source,
            next_page=row.next_page,
            fetched_pages=row.fetched_pages,
            fetched_items=row.fetched_items,
            reported_total=row.reported_total,
            exhausted=row.exhausted,
            bounded=row.bounded,
            error_count=row.error_count,
            last_error_type=row.last_error_type,
            last_fetched_at=row.last_fetched_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _candidate_record(
        row: SearchSnapshotCandidate,
    ) -> SearchSnapshotCandidateRecord:
        return SearchSnapshotCandidateRecord(
            id=row.id,
            source=row.source,
            identity_key=row.identity_key,
            provider_page=row.provider_page,
            payload_json=row.payload_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _item_record(row: SearchSnapshotItem) -> SearchSnapshotItemRecord:
        return SearchSnapshotItemRecord(
            id=row.id,
            ordinal=row.ordinal,
            stable_key=row.stable_key,
            source_keys_json=row.source_keys_json,
            payload_json=row.payload_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _json_list(values: Sequence[str]) -> str:
        return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))

    def create(
        self,
        *,
        query_fingerprint: str,
        selected_sources: Sequence[str],
        sort_code: str,
        page_size: int,
        ttl_seconds: int,
        now: int | None = None,
    ) -> SearchSnapshotRecord:
        current = int(time.time()) if now is None else int(now)
        snapshot = SearchSnapshot(
            id=str(uuid.uuid4()),
            query_fingerprint=query_fingerprint,
            selected_sources_json=self._json_list(selected_sources),
            sort_code=sort_code,
            page_size=max(1, int(page_size)),
            status="active",
            provider_reported_total=0,
            known_unique_total=0,
            committed_count=0,
            late_arrival_count=0,
            candidate_count=0,
            duplicate_count=0,
            cross_source_duplicate_count=0,
            cross_source_groups=0,
            total_is_exact=False,
            bounded=False,
            extension_lease_until=None,
            created_at=current,
            updated_at=current,
            expires_at=current + max(60, int(ttl_seconds)),
        )
        with self.session() as session, session.begin():
            session.add(snapshot)
            session.flush()
            for source in selected_sources:
                session.add(
                    SearchSnapshotSource(
                        snapshot_id=snapshot.id,
                        source=str(source),
                        next_page=0,
                        fetched_pages=0,
                        fetched_items=0,
                        reported_total=0,
                        exhausted=False,
                        bounded=False,
                        error_count=0,
                        last_error_type=None,
                        last_fetched_at=None,
                        created_at=current,
                        updated_at=current,
                    )
                )
            session.flush()
            return self._snapshot_record(snapshot)

    def get(
        self,
        snapshot_id: str,
        *,
        now: int | None = None,
        include_expired: bool = False,
    ) -> SearchSnapshotRecord | None:
        current = int(time.time()) if now is None else int(now)
        with self.session() as session:
            row = session.get(SearchSnapshot, snapshot_id)
            if row is None:
                return None
            if not include_expired and (
                row.status == "expired" or row.expires_at <= current
            ):
                return None
            return self._snapshot_record(row)

    def sources(self, snapshot_id: str) -> list[SearchSnapshotSourceRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(SearchSnapshotSource)
                .where(SearchSnapshotSource.snapshot_id == snapshot_id)
                .order_by(SearchSnapshotSource.source.asc())
            ).all()
            return [self._source_record(row) for row in rows]

    def candidates(
        self,
        snapshot_id: str,
    ) -> list[SearchSnapshotCandidateRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(SearchSnapshotCandidate)
                .where(SearchSnapshotCandidate.snapshot_id == snapshot_id)
                .order_by(
                    SearchSnapshotCandidate.provider_page.asc(),
                    SearchSnapshotCandidate.id.asc(),
                )
            ).all()
            return [self._candidate_record(row) for row in rows]

    def items(self, snapshot_id: str) -> list[SearchSnapshotItemRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(SearchSnapshotItem)
                .where(SearchSnapshotItem.snapshot_id == snapshot_id)
                .order_by(SearchSnapshotItem.ordinal.asc())
            ).all()
            return [self._item_record(row) for row in rows]

    def page_items(
        self,
        snapshot_id: str,
        *,
        page: int,
        page_size: int,
    ) -> list[SearchSnapshotItemRecord]:
        safe_page = max(0, int(page))
        safe_size = max(1, int(page_size))
        start = safe_page * safe_size
        with self.session() as session:
            rows = session.scalars(
                select(SearchSnapshotItem)
                .where(
                    SearchSnapshotItem.snapshot_id == snapshot_id,
                    SearchSnapshotItem.ordinal >= start,
                    SearchSnapshotItem.ordinal < start + safe_size,
                )
                .order_by(SearchSnapshotItem.ordinal.asc())
            ).all()
            return [self._item_record(row) for row in rows]

    def try_claim_extension(
        self,
        snapshot_id: str,
        *,
        lease_seconds: int = 60,
        now: int | None = None,
    ) -> bool:
        current = int(time.time()) if now is None else int(now)
        lease_until = current + max(5, int(lease_seconds))
        with self.session() as session:
            result = session.execute(
                update(SearchSnapshot)
                .where(
                    SearchSnapshot.id == snapshot_id,
                    SearchSnapshot.status == "active",
                    SearchSnapshot.expires_at > current,
                    or_(
                        SearchSnapshot.extension_lease_until.is_(None),
                        SearchSnapshot.extension_lease_until < current,
                    ),
                )
                .values(
                    extension_lease_until=lease_until,
                    updated_at=current,
                )
            )
            session.commit()
            return bool(result.rowcount)

    def release_extension(
        self,
        snapshot_id: str,
        *,
        ttl_seconds: int,
        now: int | None = None,
    ) -> None:
        current = int(time.time()) if now is None else int(now)
        with self.session() as session:
            session.execute(
                update(SearchSnapshot)
                .where(SearchSnapshot.id == snapshot_id)
                .values(
                    extension_lease_until=None,
                    updated_at=current,
                    expires_at=current + max(60, int(ttl_seconds)),
                )
            )
            session.commit()

    def touch(
        self,
        snapshot_id: str,
        *,
        ttl_seconds: int,
        now: int | None = None,
    ) -> None:
        current = int(time.time()) if now is None else int(now)
        with self.session() as session:
            session.execute(
                update(SearchSnapshot)
                .where(
                    SearchSnapshot.id == snapshot_id,
                    SearchSnapshot.status != "expired",
                )
                .values(
                    updated_at=current,
                    expires_at=current + max(60, int(ttl_seconds)),
                )
            )
            session.commit()

    def record_source_success(
        self,
        snapshot_id: str,
        *,
        source: str,
        provider_page: int,
        reported_total: int,
        has_next: bool,
        accepted_items: int,
        max_pages_reached: bool,
        now: int | None = None,
    ) -> SearchSnapshotSourceRecord:
        current = int(time.time()) if now is None else int(now)
        with self.session() as session:
            row = session.scalar(
                select(SearchSnapshotSource).where(
                    SearchSnapshotSource.snapshot_id == snapshot_id,
                    SearchSnapshotSource.source == source,
                )
            )
            if row is None:
                raise LookupError("Search snapshot source not found")
            row.next_page = max(row.next_page, int(provider_page) + 1)
            row.fetched_pages += 1
            row.fetched_items += max(0, int(accepted_items))
            row.reported_total = max(row.reported_total, max(0, int(reported_total)))
            row.bounded = bool(max_pages_reached and has_next)
            row.exhausted = (not bool(has_next)) or row.bounded
            row.last_error_type = None
            row.last_fetched_at = current
            row.updated_at = current
            session.commit()
            return self._source_record(row)

    def record_source_error(
        self,
        snapshot_id: str,
        *,
        source: str,
        error_type: str,
        now: int | None = None,
    ) -> SearchSnapshotSourceRecord:
        current = int(time.time()) if now is None else int(now)
        safe_error = str(error_type or "ProviderSearchError")[:128]
        with self.session() as session:
            row = session.scalar(
                select(SearchSnapshotSource).where(
                    SearchSnapshotSource.snapshot_id == snapshot_id,
                    SearchSnapshotSource.source == source,
                )
            )
            if row is None:
                raise LookupError("Search snapshot source not found")
            row.error_count += 1
            row.last_error_type = safe_error
            # A failed provider is terminal for this immutable snapshot. A new
            # search creates a fresh snapshot and can retry without changing
            # already served page boundaries.
            row.exhausted = True
            row.bounded = False
            row.updated_at = current
            session.commit()
            return self._source_record(row)

    def upsert_candidates(
        self,
        snapshot_id: str,
        *,
        source: str,
        provider_page: int,
        candidates: Iterable[tuple[str, dict[str, Any]]],
        now: int | None = None,
    ) -> int:
        """Persist a provider page with bounded round-trips.

        SEARCH-003 can receive dozens of candidates per provider page.  The
        original implementation executed one SELECT per candidate before every
        insert, which becomes prohibitively slow against a remote PostgreSQL
        database.  Fetch existing identities once, update the rare existing
        rows in-memory, and bulk-insert the new rows in one executemany call.
        """

        current = int(time.time()) if now is None else int(now)
        safe_page = max(0, int(provider_page))
        prepared: list[tuple[str, str]] = []
        for identity_key, payload in candidates:
            prepared.append(
                (
                    str(identity_key),
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
            )
        if not prepared:
            return 0

        identity_keys = [identity_key for identity_key, _payload_json in prepared]
        with self.session() as session, session.begin():
            existing_rows = session.scalars(
                select(SearchSnapshotCandidate).where(
                    SearchSnapshotCandidate.snapshot_id == snapshot_id,
                    SearchSnapshotCandidate.source == source,
                    SearchSnapshotCandidate.identity_key.in_(identity_keys),
                )
            ).all()
            existing = {row.identity_key: row for row in existing_rows}

            new_rows: list[dict[str, Any]] = []
            for identity_key, payload_json in prepared:
                row = existing.get(identity_key)
                if row is None:
                    new_rows.append(
                        {
                            "snapshot_id": snapshot_id,
                            "source": source,
                            "identity_key": identity_key,
                            "provider_page": safe_page,
                            "payload_json": payload_json,
                            "created_at": current,
                            "updated_at": current,
                        }
                    )
                    continue
                row.provider_page = min(row.provider_page, safe_page)
                row.payload_json = payload_json
                row.updated_at = current

            if new_rows:
                session.execute(insert(SearchSnapshotCandidate), new_rows)
            session.flush()
            return len(new_rows)

    def replace_items(
        self,
        snapshot_id: str,
        *,
        items: Sequence[dict[str, Any]],
        provider_reported_total: int,
        candidate_count: int,
        duplicate_count: int,
        cross_source_duplicate_count: int,
        cross_source_groups: int,
        total_is_exact: bool,
        bounded: bool,
        committed_count: int,
        late_arrival_count: int,
        now: int | None = None,
    ) -> SearchSnapshotRecord:
        current = int(time.time()) if now is None else int(now)
        with self.session() as session, session.begin():
            session.execute(
                delete(SearchSnapshotItem).where(
                    SearchSnapshotItem.snapshot_id == snapshot_id
                )
            )
            item_rows = [
                {
                    "snapshot_id": snapshot_id,
                    "ordinal": ordinal,
                    "stable_key": str(item["stable_key"]),
                    "source_keys_json": json.dumps(
                        list(item.get("source_keys") or []),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    "payload_json": json.dumps(
                        item["payload"],
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "created_at": current,
                    "updated_at": current,
                }
                for ordinal, item in enumerate(items)
            ]
            if item_rows:
                session.execute(insert(SearchSnapshotItem), item_rows)
            row = session.get(SearchSnapshot, snapshot_id)
            if row is None:
                raise LookupError("Search snapshot not found")
            row.provider_reported_total = max(0, int(provider_reported_total))
            row.known_unique_total = len(items)
            row.committed_count = max(0, min(int(committed_count), len(items)))
            row.late_arrival_count = max(0, int(late_arrival_count))
            row.candidate_count = max(0, int(candidate_count))
            row.duplicate_count = max(0, int(duplicate_count))
            row.cross_source_duplicate_count = max(
                0,
                int(cross_source_duplicate_count),
            )
            row.cross_source_groups = max(0, int(cross_source_groups))
            row.total_is_exact = bool(total_is_exact)
            row.bounded = bool(bounded)
            if total_is_exact:
                row.status = "complete"
            elif row.status == "complete":
                row.status = "active"
            row.updated_at = current
            session.flush()
            return self._snapshot_record(row)

    def commit_boundary(
        self,
        snapshot_id: str,
        *,
        requested_commit_count: int,
        now: int | None = None,
    ) -> SearchSnapshotRecord:
        """Advance the immutable served prefix without rewriting materialized rows."""

        current = int(time.time()) if now is None else int(now)
        with self.session() as session, session.begin():
            row = session.get(SearchSnapshot, snapshot_id)
            if row is None:
                raise LookupError("Search snapshot not found")
            row.committed_count = max(
                row.committed_count,
                min(max(0, int(requested_commit_count)), row.known_unique_total),
            )
            row.updated_at = current
            session.flush()
            return self._snapshot_record(row)

    def cleanup_expired(
        self,
        *,
        now: int | None = None,
        limit: int = 100,
    ) -> int:
        current = int(time.time()) if now is None else int(now)
        safe_limit = max(1, min(int(limit), 1000))
        with self.session() as session, session.begin():
            ids = list(
                session.scalars(
                    select(SearchSnapshot.id)
                    .where(
                        or_(
                            SearchSnapshot.expires_at <= current,
                            SearchSnapshot.status == "expired",
                        )
                    )
                    .order_by(SearchSnapshot.expires_at.asc())
                    .limit(safe_limit)
                ).all()
            )
            if not ids:
                return 0
            result = session.execute(
                delete(SearchSnapshot).where(SearchSnapshot.id.in_(ids))
            )
            return int(result.rowcount or 0)

    def candidate_count(self, snapshot_id: str) -> int:
        """Return the bounded candidate count without loading payloads."""

        with self.session() as session:
            return int(
                session.scalar(
                    select(func.count(SearchSnapshotCandidate.id)).where(
                        SearchSnapshotCandidate.snapshot_id == snapshot_id
                    )
                )
                or 0
            )

    def candidate_counts_by_source(self, snapshot_id: str) -> dict[str, int]:
        """Return unique persisted candidate counts for every provider.

        SEARCH-003 uses this coverage map to establish a stable global page
        boundary. A provider with fewer than ``required_count`` accepted
        publications can still contribute an unseen item to that boundary, so
        its cursor must advance (within the configured bounds) even when the
        aggregate candidate pool is already large enough.
        """

        with self.session() as session:
            rows = session.execute(
                select(
                    SearchSnapshotCandidate.source,
                    func.count(SearchSnapshotCandidate.id),
                )
                .where(SearchSnapshotCandidate.snapshot_id == snapshot_id)
                .group_by(SearchSnapshotCandidate.source)
            ).all()
        return {str(source): int(count or 0) for source, count in rows}

    def counts(self) -> dict[str, int]:
        with self.session() as session:
            return {
                "snapshots": int(session.scalar(select(func.count(SearchSnapshot.id))) or 0),
                "sources": int(session.scalar(select(func.count(SearchSnapshotSource.id))) or 0),
                "candidates": int(session.scalar(select(func.count(SearchSnapshotCandidate.id))) or 0),
                "items": int(session.scalar(select(func.count(SearchSnapshotItem.id))) or 0),
            }

    def aggregate_summary(
        self,
        snapshot_id: str,
        *,
        now: int | None = None,
    ) -> dict[str, Any] | None:
        """Return a secret-free browser-readable summary for verification.

        Query text and raw provider payloads are intentionally omitted. The
        opaque snapshot identifier is safe to expose because it carries no
        authorization semantics and expires with the snapshot TTL.
        """

        current = int(time.time()) if now is None else int(now)
        snapshot = self.get(snapshot_id, now=current, include_expired=True)
        if snapshot is None:
            return None
        source_rows = self.sources(snapshot_id)
        return {
            **snapshot.public_summary(),
            "age_seconds": max(0, current - snapshot.created_at),
            "expires_in_seconds": max(0, snapshot.expires_at - current),
            "expired": snapshot.expires_at <= current or snapshot.status == "expired",
            "sources": {
                row.source: {
                    "next_page": row.next_page,
                    "fetched_pages": row.fetched_pages,
                    "fetched_items": row.fetched_items,
                    "reported_total": row.reported_total,
                    "exhausted": row.exhausted,
                    "bounded": row.bounded,
                    "error_count": row.error_count,
                    "last_error_type": row.last_error_type,
                    "last_fetched_at": row.last_fetched_at,
                }
                for row in source_rows
            },
        }
