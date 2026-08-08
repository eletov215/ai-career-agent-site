"""Repository for persisted provider synchronization runs."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError

from domain import SyncRunRecord
from models import SyncRun

from .base import RepositoryBase


_ACTIVE_STATUSES = ("queued", "running")


def _advisory_key(namespace: str, source: str) -> int:
    digest = hashlib.sha256(f"{namespace}:{source}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFF_FFFF_FFFF_FFFF


class SyncRunRepository(RepositoryBase):
    """Record synchronization lifecycle without coupling workers to ORM."""

    @staticmethod
    def _record(row: SyncRun) -> SyncRunRecord:
        return SyncRunRecord(
            id=row.id,
            source=row.source,
            trigger=row.trigger,
            status=row.status,
            started_at=row.started_at,
            finished_at=row.finished_at,
            target=row.target,
            processed=row.processed,
            saved=row.saved,
            cursor=row.cursor,
            error_type=row.error_type,
            error_message=row.error_message,
            details_json=row.details_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _details(details: dict[str, Any] | None) -> str | None:
        return (
            json.dumps(details, ensure_ascii=False, sort_keys=True)
            if details
            else None
        )

    def _serialize_source_transaction(self, session, source: str) -> None:  # noqa: ANN001
        if self.engine.dialect.name == "postgresql":
            session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _advisory_key("sync-run-queue", source)},
            )

    def _active_row(self, session, source: str) -> SyncRun | None:  # noqa: ANN001
        return session.scalar(
            select(SyncRun)
            .where(
                SyncRun.source == source,
                SyncRun.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(SyncRun.created_at.asc())
            .limit(1)
        )

    def enqueue(
        self,
        *,
        source: str,
        trigger: str,
        target: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> SyncRunRecord:
        """Create one durable queued run, returning the active run if present."""

        now = int(time.time())
        try:
            with self.session() as session, session.begin():
                self._serialize_source_transaction(session, source)
                active = self._active_row(session, source)
                if active is not None:
                    return self._record(active)
                row = SyncRun(
                    id=str(uuid.uuid4()),
                    source=source,
                    trigger=trigger,
                    status="queued",
                    # The existing schema predates queued jobs and requires
                    # started_at. For queued rows this value is the request time;
                    # claim() replaces it with the real execution start time.
                    started_at=now,
                    finished_at=None,
                    target=target,
                    processed=0,
                    saved=0,
                    cursor=None,
                    error_type=None,
                    error_message=None,
                    details_json=self._details(details),
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.flush()
                return self._record(row)
        except IntegrityError:
            # The partial unique index closes the race between multiple web
            # instances. A concurrent request won; return that active run.
            active = self.active(source)
            if active is not None:
                return active
            raise

    def start(
        self,
        *,
        source: str,
        trigger: str,
        target: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> SyncRunRecord:
        """Start an immediate run.

        Callers that may race should catch IntegrityError or use active() first.
        The external worker normally claims a queued run before using this.
        """

        now = int(time.time())
        row = SyncRun(
            id=str(uuid.uuid4()),
            source=source,
            trigger=trigger,
            status="running",
            started_at=now,
            finished_at=None,
            target=target,
            processed=0,
            saved=0,
            cursor=None,
            error_type=None,
            error_message=None,
            details_json=self._details(details),
            created_at=now,
            updated_at=now,
        )
        with self.session() as session:
            session.add(row)
            session.commit()
            return self._record(row)

    def claim(self, run_id: str) -> SyncRunRecord | None:
        """Atomically move a queued run to running."""

        now = int(time.time())
        with self.session() as session, session.begin():
            row = session.get(SyncRun, run_id)
            if row is None or row.status != "queued":
                return None
            row.status = "running"
            row.started_at = now
            row.updated_at = now
            session.flush()
            return self._record(row)

    def claim_next(self, source: str) -> SyncRunRecord | None:
        """Claim the oldest queued run for a source."""

        now = int(time.time())
        with self.session() as session, session.begin():
            self._serialize_source_transaction(session, source)
            row = session.scalar(
                select(SyncRun)
                .where(
                    SyncRun.source == source,
                    SyncRun.status == "queued",
                )
                .order_by(SyncRun.created_at.asc())
                .limit(1)
            )
            if row is None:
                return None
            row.status = "running"
            row.started_at = now
            row.updated_at = now
            session.flush()
            return self._record(row)

    def set_target(self, run_id: str, *, target: int) -> SyncRunRecord:
        now = int(time.time())
        with self.session() as session:
            row = session.get(SyncRun, run_id)
            if row is None:
                raise LookupError("Sync run not found")
            if row.status not in _ACTIVE_STATUSES:
                raise RuntimeError("Only an active sync target can be updated")
            row.target = max(0, int(target))
            row.updated_at = now
            session.commit()
            return self._record(row)

    def heartbeat(
        self,
        run_id: str,
        *,
        processed: int,
        saved: int,
        cursor: str | None = None,
    ) -> SyncRunRecord:
        now = int(time.time())
        with self.session() as session:
            row = session.get(SyncRun, run_id)
            if row is None:
                raise LookupError("Sync run not found")
            if row.status != "running":
                raise RuntimeError("Only a running sync can be updated")
            row.processed = int(processed)
            row.saved = int(saved)
            row.cursor = cursor
            row.updated_at = now
            session.commit()
            return self._record(row)

    def finish(
        self,
        run_id: str,
        *,
        status: str,
        processed: int,
        saved: int,
        cursor: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> SyncRunRecord:
        now = int(time.time())
        with self.session() as session:
            row = session.get(SyncRun, run_id)
            if row is None:
                raise LookupError("Sync run not found")
            row.status = status
            row.finished_at = now
            row.processed = int(processed)
            row.saved = int(saved)
            row.cursor = cursor
            row.error_type = error_type
            row.error_message = error_message
            if details is not None:
                row.details_json = self._details(details)
            row.updated_at = now
            session.commit()
            return self._record(row)

    def fail_stale(
        self,
        source: str,
        *,
        stale_before: int,
        error_type: str = "WorkerLost",
        error_message: str = "Synchronization worker stopped before completion.",
    ) -> int:
        """Close abandoned running rows so a replacement worker can continue."""

        now = int(time.time())
        with self.session() as session:
            result = session.execute(
                update(SyncRun)
                .where(
                    SyncRun.source == source,
                    SyncRun.status == "running",
                    SyncRun.updated_at < int(stale_before),
                )
                .values(
                    status="failed",
                    finished_at=now,
                    error_type=error_type,
                    error_message=error_message,
                    updated_at=now,
                )
            )
            session.commit()
            return int(result.rowcount or 0)

    def active(self, source: str) -> SyncRunRecord | None:
        with self.session() as session:
            row = self._active_row(session, source)
            return self._record(row) if row else None

    def latest(self, source: str) -> SyncRunRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(SyncRun)
                .where(SyncRun.source == source)
                .order_by(SyncRun.created_at.desc(), SyncRun.updated_at.desc())
                .limit(1)
            )
            return self._record(row) if row else None

    def latest_succeeded(self, source: str) -> SyncRunRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(SyncRun)
                .where(
                    SyncRun.source == source,
                    SyncRun.status == "succeeded",
                )
                .order_by(SyncRun.finished_at.desc(), SyncRun.updated_at.desc())
                .limit(1)
            )
            return self._record(row) if row else None
