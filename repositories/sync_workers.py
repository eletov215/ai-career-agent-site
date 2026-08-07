"""Repository for synchronization worker heartbeats."""

from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import delete, select

from domain import SyncWorkerRecord
from models import SyncWorker

from .base import RepositoryBase


class SyncWorkerRepository(RepositoryBase):
    """Persist worker liveness independently of the web process."""

    @staticmethod
    def _record(row: SyncWorker) -> SyncWorkerRecord:
        return SyncWorkerRecord(
            id=row.id,
            source=row.source,
            status=row.status,
            current_run_id=row.current_run_id,
            started_at=row.started_at,
            heartbeat_at=row.heartbeat_at,
            details_json=row.details_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def heartbeat(
        self,
        *,
        worker_id: str,
        source: str,
        status: str,
        current_run_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> SyncWorkerRecord:
        now = int(time.time())
        with self.session() as session:
            row = session.get(SyncWorker, worker_id)
            if row is None:
                row = SyncWorker(
                    id=worker_id,
                    source=source,
                    status=status,
                    current_run_id=current_run_id,
                    started_at=now,
                    heartbeat_at=now,
                    details_json=(
                        json.dumps(details, ensure_ascii=False, sort_keys=True)
                        if details
                        else None
                    ),
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.source = source
                row.status = status
                row.current_run_id = current_run_id
                row.heartbeat_at = now
                if details is not None:
                    row.details_json = json.dumps(
                        details,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                row.updated_at = now
            session.commit()
            return self._record(row)

    def remove(self, worker_id: str) -> None:
        with self.session() as session:
            session.execute(delete(SyncWorker).where(SyncWorker.id == worker_id))
            session.commit()

    def active(self, source: str, *, stale_after: int) -> list[SyncWorkerRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(SyncWorker)
                .where(
                    SyncWorker.source == source,
                    SyncWorker.heartbeat_at >= int(stale_after),
                )
                .order_by(SyncWorker.heartbeat_at.desc())
            ).all()
            return [self._record(row) for row in rows]

    def latest(self, source: str) -> SyncWorkerRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(SyncWorker)
                .where(SyncWorker.source == source)
                .order_by(SyncWorker.heartbeat_at.desc())
                .limit(1)
            )
            return self._record(row) if row else None

    def prune_stale(self, *, stale_before: int) -> int:
        with self.session() as session:
            result = session.execute(
                delete(SyncWorker).where(
                    SyncWorker.heartbeat_at < int(stale_before)
                )
            )
            session.commit()
            return int(result.rowcount or 0)
