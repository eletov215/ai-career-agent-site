"""Repository for persisted provider synchronization runs."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import select

from domain import SyncRunRecord
from models import SyncRun

from .base import RepositoryBase


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

    def start(
        self,
        *,
        source: str,
        trigger: str,
        target: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> SyncRunRecord:
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
            details_json=json.dumps(details, ensure_ascii=False) if details else None,
            created_at=now,
            updated_at=now,
        )
        with self.session() as session:
            session.add(row)
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
                row.details_json = json.dumps(details, ensure_ascii=False)
            row.updated_at = now
            session.commit()
            return self._record(row)

    def latest(self, source: str) -> SyncRunRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(SyncRun)
                .where(SyncRun.source == source)
                .order_by(SyncRun.started_at.desc(), SyncRun.created_at.desc())
                .limit(1)
            )
            return self._record(row) if row else None
