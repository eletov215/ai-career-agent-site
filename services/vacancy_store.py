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
            external_id = normalized["external_id"]
            source = normalized["source"]
            if not source or not external_id:
                continue
            payloads.append(
                {
                    "source": source,
                    "external_id": external_id,
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
        return self.repository.upsert_source_records(payloads)

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
                result.append(normalize_vacancy_mapping(item).as_mapping())
        return result

    def count(self, **filters: Any) -> int:
        return self.repository.count(**filters)

    def source_age_seconds(self, source: str) -> int | None:
        return self.repository.source_age_seconds(source)
