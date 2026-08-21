"""Repository for safe operational source-health aggregates."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from domain.source_health import SourceHealthRecord
from models.source_health import SourceHealthState

from .base import RepositoryBase


class SourceHealthRepository(RepositoryBase):
    @staticmethod
    def _record(row: SourceHealthState) -> SourceHealthRecord:
        return SourceHealthRecord(
            provider=row.provider,
            availability=row.availability,
            configured=bool(row.configured),
            last_attempt_at=row.last_attempt_at,
            last_success_at=row.last_success_at,
            last_failure_at=row.last_failure_at,
            last_latency_ms=row.last_latency_ms,
            consecutive_failures=max(0, int(row.consecutive_failures or 0)),
            error_category=row.error_category,
            error_code=row.error_code,
            cache_observed_at=row.cache_observed_at,
            cache_item_count=row.cache_item_count,
            details_json=row.details_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def get(self, provider: str) -> SourceHealthRecord | None:
        with self.session() as session:
            row = session.get(SourceHealthState, provider)
            return self._record(row) if row else None

    def list(self) -> list[SourceHealthRecord]:
        with self.session() as session:
            rows = session.scalars(select(SourceHealthState).order_by(SourceHealthState.provider)).all()
            return [self._record(row) for row in rows]

    def record_observation(
        self,
        *,
        provider: str,
        configured: bool,
        success: bool,
        availability: str,
        latency_ms: int | None,
        error_category: str | None,
        error_code: str | None,
        cache_item_count: int | None,
        details_json: str | None,
        now: int | None = None,
    ) -> SourceHealthRecord:
        timestamp = int(time.time()) if now is None else int(now)
        try:
            with self.session() as session, session.begin():
                row = session.scalar(
                    select(SourceHealthState)
                    .where(SourceHealthState.provider == provider)
                    .with_for_update()
                )
                if row is None:
                    row = SourceHealthState(
                        provider=provider,
                        availability="unknown",
                        configured=configured,
                        consecutive_failures=0,
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                    session.add(row)
                row.configured = bool(configured)
                row.last_attempt_at = timestamp
                row.last_latency_ms = latency_ms
                row.updated_at = timestamp
                if cache_item_count is not None:
                    row.cache_observed_at = timestamp
                    row.cache_item_count = max(0, int(cache_item_count))
                if success:
                    row.availability = availability
                    row.last_success_at = timestamp
                    row.consecutive_failures = 0
                    row.error_category = None
                    row.error_code = None
                else:
                    row.availability = availability
                    row.last_failure_at = timestamp
                    row.consecutive_failures = max(0, int(row.consecutive_failures or 0)) + 1
                    row.error_category = error_category
                    row.error_code = error_code
                if details_json is not None:
                    row.details_json = details_json
                session.flush()
                return self._record(row)
        except IntegrityError:
            # A concurrent first observation may win the insert race. Retry once
            # through the now-existing row without exposing provider payloads.
            with self.session() as session, session.begin():
                row = session.scalar(
                    select(SourceHealthState)
                    .where(SourceHealthState.provider == provider)
                    .with_for_update()
                )
                if row is None:
                    raise
                row.configured = bool(configured)
                row.last_attempt_at = timestamp
                row.last_latency_ms = latency_ms
                row.updated_at = timestamp
                if success:
                    row.availability = availability
                    row.last_success_at = timestamp
                    row.consecutive_failures = 0
                    row.error_category = None
                    row.error_code = None
                else:
                    row.availability = availability
                    row.last_failure_at = timestamp
                    row.consecutive_failures = max(0, int(row.consecutive_failures or 0)) + 1
                    row.error_category = error_category
                    row.error_code = error_code
                if cache_item_count is not None:
                    row.cache_observed_at = timestamp
                    row.cache_item_count = max(0, int(cache_item_count))
                if details_json is not None:
                    row.details_json = details_json
                session.flush()
                return self._record(row)

    def record_cache(
        self,
        *,
        provider: str,
        configured: bool,
        availability: str,
        cache_item_count: int,
        now: int | None = None,
    ) -> SourceHealthRecord:
        timestamp = int(time.time()) if now is None else int(now)
        with self.session() as session, session.begin():
            row = session.scalar(
                select(SourceHealthState)
                .where(SourceHealthState.provider == provider)
                .with_for_update()
            )
            if row is None:
                row = SourceHealthState(
                    provider=provider,
                    availability=availability,
                    configured=configured,
                    consecutive_failures=0,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                session.add(row)
            row.configured = bool(configured)
            row.cache_observed_at = timestamp
            row.cache_item_count = max(0, int(cache_item_count))
            row.updated_at = timestamp
            session.flush()
            return self._record(row)
