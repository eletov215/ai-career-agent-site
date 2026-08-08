"""Repository for durable incremental synchronization checkpoints."""

from __future__ import annotations

import time

from domain import SyncCheckpointRecord
from models import SyncCheckpoint

from .base import RepositoryBase


class SyncCheckpointRepository(RepositoryBase):
    """Persist source watermarks, continuation cursors, and retry backoff."""

    @staticmethod
    def _record(row: SyncCheckpoint) -> SyncCheckpointRecord:
        return SyncCheckpointRecord(
            source=row.source,
            watermark_at=row.watermark_at,
            pending_from_at=row.pending_from_at,
            pending_to_at=row.pending_to_at,
            pending_offset=row.pending_offset,
            pending_limit=row.pending_limit,
            pending_total=row.pending_total,
            last_success_run_id=row.last_success_run_id,
            last_success_at=row.last_success_at,
            last_cleanup_at=row.last_cleanup_at,
            consecutive_failures=int(row.consecutive_failures or 0),
            next_retry_at=row.next_retry_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _get_or_create(session, source: str, *, now: int) -> SyncCheckpoint:  # noqa: ANN001
        row = session.get(SyncCheckpoint, source)
        if row is None:
            row = SyncCheckpoint(
                source=source,
                watermark_at=None,
                pending_from_at=None,
                pending_to_at=None,
                pending_offset=None,
                pending_limit=None,
                pending_total=None,
                last_success_run_id=None,
                last_success_at=None,
                last_cleanup_at=None,
                consecutive_failures=0,
                next_retry_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
        return row

    def get(self, source: str) -> SyncCheckpointRecord | None:
        with self.session() as session:
            row = session.get(SyncCheckpoint, source)
            return self._record(row) if row else None

    def ensure(self, source: str) -> SyncCheckpointRecord:
        now = int(time.time())
        with self.session() as session:
            row = self._get_or_create(session, source, now=now)
            session.commit()
            return self._record(row)

    def begin_window(
        self,
        source: str,
        *,
        from_at: int,
        to_at: int,
        offset: int,
        limit: int,
    ) -> SyncCheckpointRecord:
        """Create an incremental window unless a continuation already exists."""

        now = int(time.time())
        with self.session() as session:
            row = self._get_or_create(session, source, now=now)
            if row.pending_to_at is None:
                row.pending_from_at = int(from_at)
                row.pending_to_at = int(to_at)
                row.pending_offset = max(1, int(offset))
                row.pending_limit = max(1, int(limit))
                row.pending_total = None
            row.updated_at = now
            session.commit()
            return self._record(row)

    def advance_window(
        self,
        source: str,
        *,
        next_offset: int,
        total: int | None = None,
    ) -> SyncCheckpointRecord:
        now = int(time.time())
        with self.session() as session:
            row = self._get_or_create(session, source, now=now)
            row.pending_offset = max(1, int(next_offset))
            if total is not None:
                row.pending_total = max(0, int(total))
            row.updated_at = now
            session.commit()
            return self._record(row)

    def complete_success(
        self,
        source: str,
        *,
        run_id: str,
        watermark_at: int,
        cleanup_at: int | None = None,
        clear_pending: bool = True,
    ) -> SyncCheckpointRecord:
        now = int(time.time())
        with self.session() as session:
            row = self._get_or_create(session, source, now=now)
            row.watermark_at = int(watermark_at)
            if clear_pending:
                row.pending_from_at = None
                row.pending_to_at = None
                row.pending_offset = None
                row.pending_limit = None
                row.pending_total = None
            row.last_success_run_id = run_id
            row.last_success_at = now
            if cleanup_at is not None:
                row.last_cleanup_at = int(cleanup_at)
            row.consecutive_failures = 0
            row.next_retry_at = None
            row.updated_at = now
            session.commit()
            return self._record(row)

    def record_partial_success(
        self,
        source: str,
        *,
        run_id: str,
    ) -> SyncCheckpointRecord:
        """Keep the pending window while recording a successful continuation chunk."""

        now = int(time.time())
        with self.session() as session:
            row = self._get_or_create(session, source, now=now)
            row.last_success_run_id = run_id
            row.last_success_at = now
            row.consecutive_failures = 0
            row.next_retry_at = None
            row.updated_at = now
            session.commit()
            return self._record(row)

    def record_cleanup(self, source: str, *, cleanup_at: int) -> SyncCheckpointRecord:
        now = int(time.time())
        with self.session() as session:
            row = self._get_or_create(session, source, now=now)
            row.last_cleanup_at = int(cleanup_at)
            row.updated_at = now
            session.commit()
            return self._record(row)

    def record_failure(
        self,
        source: str,
        *,
        base_seconds: int,
        max_seconds: int,
        now: int | None = None,
    ) -> SyncCheckpointRecord:
        current = int(time.time()) if now is None else int(now)
        with self.session() as session:
            row = self._get_or_create(session, source, now=current)
            failures = int(row.consecutive_failures or 0) + 1
            delay = min(
                max(1, int(max_seconds)),
                max(1, int(base_seconds)) * (2 ** min(failures - 1, 12)),
            )
            row.consecutive_failures = failures
            row.next_retry_at = current + delay
            row.updated_at = current
            session.commit()
            return self._record(row)

    def retry_due(self, source: str, *, now: int | None = None) -> bool:
        checkpoint = self.get(source)
        if checkpoint is None or checkpoint.next_retry_at is None:
            return True
        current = int(time.time()) if now is None else int(now)
        return checkpoint.next_retry_at <= current
