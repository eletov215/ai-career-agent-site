from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import Engine

from database import DatabaseRuntime, create_database
from repositories import VacancyRepository

from .vacancy_deduplication import (
    DEDUP_VERSION,
    compare_vacancies,
    dedup_key_for,
    deduplicate_vacancies,
)
from .vacancy_normalizer import normalize_datetime, normalize_vacancy_mapping




@dataclass(frozen=True, slots=True)
class VacancyCleanupResult:
    closed: int = 0
    purged: int = 0

    def as_dict(self) -> dict[str, int]:
        return {"closed": self.closed, "purged": self.purged}


class VacancyStore:
    """Application-facing vacancy cache service.

    SQLAlchemy statements live in :class:`repositories.VacancyRepository`.
    This service is responsible only for normalizing provider payloads and
    preserving the public API used by routes and tests.
    """

    def __init__(self, database: DatabaseRuntime | Engine | Path | str):
        self._owned_runtime: DatabaseRuntime | None = None
        if isinstance(database, (DatabaseRuntime, Engine)):
            repository_database = database
        else:
            raw = str(database)
            if "://" not in raw:
                path = Path(raw).expanduser().resolve()
                raw = f"sqlite:///{path.as_posix()}"
            runtime = create_database(raw)
            self._owned_runtime = runtime
            repository_database = runtime
        self.repository = VacancyRepository(repository_database)

    @property
    def engine(self):  # noqa: ANN201 - compatibility for existing tests/tools
        return self.repository.engine

    def init(self) -> None:
        """Create vacancy tables for isolated compatibility tests only."""

        self.repository.init_schema()

    def close(self) -> None:
        if self._owned_runtime is not None:
            self._owned_runtime.dispose()

    @staticmethod
    def _search_blob(item: dict[str, Any]) -> str:
        values = [
            item.get("title"),
            item.get("company"),
            item.get("location"),
            item.get("description"),
            item.get("requirements"),
            item.get("schedule"),
            item.get("employment"),
            item.get("experience"),
            item.get("work_format"),
            item.get("employment_code"),
            item.get("experience_code"),
            item.get("currency"),
        ]
        return " ".join(str(value or "") for value in values).lower()

    @staticmethod
    def _normalize_published_at(value: object | None) -> str | None:
        return normalize_datetime(value)

    def upsert_many(
        self,
        items: Iterable[dict[str, Any]],
        *,
        run_id: str | None = None,
        seen_at: int | None = None,
    ) -> int:
        now = int(time.time()) if seen_at is None else int(seen_at)
        payloads: list[dict[str, Any]] = []
        for item in items:
            normalized = normalize_vacancy_mapping(item).as_mapping()
            normalized["dedup_key"] = dedup_key_for(normalized)
            normalized["dedup_version"] = DEDUP_VERSION
            external_id = normalized["external_id"]
            source = normalized["source"]
            if not source or not external_id:
                continue
            payloads.append(
                {
                    "source": source,
                    "external_id": external_id,
                    "dedup_key": normalized["dedup_key"],
                    "dedup_version": normalized["dedup_version"],
                    "title": normalized["title"],
                    "company": normalized["company"],
                    "salary_from": normalized["salary_from"],
                    "salary_to": normalized["salary_to"],
                    "currency": normalized["currency"] or None,
                    "location": normalized["location"],
                    "remote": normalized["remote"],
                    "work_format": normalized["work_format"],
                    "employment_code": normalized["employment_code"],
                    "experience_code": normalized["experience_code"],
                    "schedule": normalized["schedule"],
                    "employment": normalized["employment"],
                    "experience": normalized["experience"],
                    "description": normalized["description"],
                    "requirements": normalized["requirements"],
                    "published_at": normalized["published_at"],
                    "url": normalized["url"],
                    "search_text": self._search_blob(normalized),
                    "raw_json": json.dumps(normalized, ensure_ascii=False),
                    "source_status": normalized["source_status"],
                    "source_modified_at": normalized["source_modified_at"],
                    "closed_at": normalized["closed_at"],
                    "closed_reason": normalized["closed_reason"],
                    "last_seen_run_id": run_id,
                    "last_seen_at": now,
                    "fetched_at": now,
                    "updated_at": now,
                }
            )
        self._detach_changed_group_members(payloads)
        saved = self.repository.upsert_source_records(payloads)
        self._reconcile_dedup_keys(
            {payload.get("dedup_key") for payload in payloads if payload.get("dedup_key")}
        )
        return saved

    @staticmethod
    def _record_mapping(record) -> dict[str, Any]:  # noqa: ANN001
        try:
            payload = json.loads(record.raw_json or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload.update(
            {
                "source": record.source,
                "external_id": record.external_id,
                "title": record.title,
                "company": record.company,
                "salary_from": record.salary_from,
                "salary_to": record.salary_to,
                "currency": record.currency,
                "location": record.location,
                "remote": record.remote,
                "work_format": record.work_format,
                "employment_code": record.employment_code,
                "experience_code": record.experience_code,
                "schedule": record.schedule,
                "employment": record.employment,
                "experience": record.experience,
                "description": record.description,
                "requirements": record.requirements,
                "published_at": record.published_at,
                "url": record.url,
                "source_status": record.source_status,
                "dedup_key": record.dedup_key,
                "dedup_version": record.dedup_version,
            }
        )
        return payload

    def _detach_changed_group_members(
        self,
        payloads: list[dict[str, Any]],
    ) -> None:
        for payload in payloads:
            if payload.get("source_status") != "active":
                continue
            existing = self.repository.get_source(
                str(payload.get("source") or ""),
                str(payload.get("external_id") or ""),
            )
            if existing is None:
                continue
            group = self.repository.list_sources(existing.vacancy_id)
            active_others = [
                record
                for record in group
                if record.source_status == "active"
                and (record.source, record.external_id)
                != (existing.source, existing.external_id)
            ]
            if not active_others:
                continue
            incoming = dict(payload)
            decisions = [
                compare_vacancies(incoming, self._record_mapping(record))
                for record in active_others
            ]
            if decisions and all(decision.matched for decision in decisions):
                continue
            self.repository.detach_source_record(
                source=existing.source,
                external_id=existing.external_id,
                canonical_values=incoming,
                dedup_key=incoming.get("dedup_key"),
                dedup_version=int(
                    incoming.get("dedup_version") or DEDUP_VERSION
                ),
            )

    def _reconcile_dedup_keys(self, dedup_keys: set[str]) -> None:
        records = self.repository.list_sources_by_dedup_keys(dedup_keys)
        by_key: dict[str, list[Any]] = {}
        for record in records:
            if record.dedup_key:
                by_key.setdefault(record.dedup_key, []).append(record)

        for key_records in by_key.values():
            if len({record.source for record in key_records}) < 2:
                continue
            result = deduplicate_vacancies(
                self._record_mapping(record) for record in key_records
            )
            for merged in result.items:
                source_records = merged.get("source_records") or []
                source_keys = [
                    (record.get("source"), record.get("external_id"))
                    for record in source_records
                    if record.get("source") and record.get("external_id")
                ]
                if len({source for source, _ in source_keys}) < 2:
                    continue
                self.repository.merge_source_record_group(
                    source_keys=source_keys,
                    canonical_values=merged,
                    dedup_key=merged.get("dedup_key"),
                    dedup_version=int(merged.get("dedup_version") or DEDUP_VERSION),
                )

    def cleanup_source(
        self,
        *,
        source: str,
        vacancy_ttl_days: int,
        closed_retention_days: int,
        now: int | None = None,
    ) -> VacancyCleanupResult:
        """Close old postings and purge long-retained closed source rows."""

        current = int(time.time()) if now is None else int(now)
        published_cutoff = datetime.fromtimestamp(
            current,
            tz=timezone.utc,
        ) - timedelta(days=max(1, int(vacancy_ttl_days)))
        published_before = published_cutoff.isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        closed = self.repository.mark_expired_active(
            source=source,
            published_before=published_before,
            closed_at=current,
        )
        retention_seconds = max(1, int(closed_retention_days)) * 86_400
        purged = self.repository.purge_closed(
            source=source,
            closed_before=current - retention_seconds,
        )
        return VacancyCleanupResult(closed=closed, purged=purged)

    def source_status_counts(self, source: str) -> dict[str, int]:
        return self.repository.source_status_counts(source)

    def search(
        self,
        *,
        keyword: str,
        sources: list[str],
        remote_only: bool = False,
        salary_from: int | None = None,
        salary_only: bool = False,
        period_days: int = 7,
        sort: str = "date",
        limit: int = 60,
        offset: int = 0,
        region: str = "",
        experience: str = "",
        employment: str = "",
        work_format: str = "",
        currency: str = "",
    ) -> list[dict[str, Any]]:
        raw_rows = self.repository.search_raw_json(
            keyword=keyword,
            sources=sources,
            remote_only=remote_only,
            salary_from=salary_from,
            salary_only=salary_only,
            period_days=period_days,
            sort=sort,
            limit=limit,
            offset=offset,
            region=region,
            experience=experience,
            employment=employment,
            work_format=work_format,
            currency=currency,
        )
        result: list[dict[str, Any]] = []
        for raw_json in raw_rows:
            try:
                item = json.loads(raw_json or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(item, dict):
                normalized = normalize_vacancy_mapping(item).as_mapping()
                normalized["dedup_key"] = item.get("dedup_key") or dedup_key_for(normalized)
                normalized["dedup_version"] = int(item.get("dedup_version") or DEDUP_VERSION)
                result.append(normalized)
        return result

    def count(self, **filters: Any) -> int:
        return self.repository.count(**filters)

    def source_age_seconds(self, source: str) -> int | None:
        return self.repository.source_age_seconds(source)
