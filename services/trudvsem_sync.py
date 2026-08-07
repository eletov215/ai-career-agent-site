"""Hosting-independent Trudvsem synchronization application service."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, ContextManager, Protocol

from sqlalchemy.exc import IntegrityError

from config import AppSettings
from database import DatabaseRuntime
from domain import SyncRunRecord
from repositories import SyncRunRepository
from services.sync_lock import SyncExecutionLock
from services.trudvsem_provider import TrudvsemProvider
from services.vacancy_store import VacancyStore

logger = logging.getLogger(__name__)


class ProviderObservationProtocol(Protocol):
    """Minimal observation contract used by the synchronization service."""

    result_count: int | None

    def fail(
        self,
        error_type: str,
        *,
        status_code: int | None = None,
        timeout: bool = False,
    ) -> None: ...


ProviderOperationFactory = Callable[
    [str, str],
    ContextManager[ProviderObservationProtocol],
]


class _NoopProviderObservation:
    """Fallback observation that keeps this service Flask-independent."""

    result_count: int | None = None

    def fail(
        self,
        error_type: str,
        *,
        status_code: int | None = None,
        timeout: bool = False,
    ) -> None:
        del error_type, status_code, timeout


@contextmanager
def _noop_provider_operation(
    _provider: str,
    _operation: str,
):
    yield _NoopProviderObservation()


@dataclass(frozen=True, slots=True)
class SyncExecutionResult:
    """Sanitized result returned to CLI/worker callers."""

    status: str
    run: SyncRunRecord | None
    processed: int = 0
    saved: int = 0
    error_type: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"succeeded", "already_running", "locked"}

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "status": self.status,
            "run_id": self.run.id if self.run else None,
            "source": self.run.source if self.run else "trudvsem",
            "trigger": self.run.trigger if self.run else None,
            "processed": self.processed,
            "saved": self.saved,
            "error_type": self.error_type,
        }


class TrudvsemSyncService:
    """Execute and monitor Trudvsem cache synchronization outside Flask."""

    source = "trudvsem"

    def __init__(
        self,
        *,
        settings: AppSettings,
        database: DatabaseRuntime,
        vacancy_store: VacancyStore,
        sync_runs: SyncRunRepository,
        provider_factory: Callable[[], TrudvsemProvider] | None = None,
        provider_operation_factory: ProviderOperationFactory | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.database = database
        self.vacancy_store = vacancy_store
        self.sync_runs = sync_runs
        self.provider_factory = provider_factory or self._default_provider
        self.provider_operation_factory = (
            provider_operation_factory or _noop_provider_operation
        )
        self.sleeper = sleeper

    def _default_provider(self) -> TrudvsemProvider:
        return TrudvsemProvider(
            self.settings.hh_user_agent,
            per_page=10,
            timeout=(5, 45),
            scan_pages=5,
            request_attempts=self.settings.trudvsem_request_attempts,
            retry_backoff=self.settings.trudvsem_retry_backoff,
        )

    def enqueue(
        self,
        *,
        trigger: str,
        target: int | None = None,
        details: dict[str, object] | None = None,
    ) -> SyncRunRecord:
        target_value = max(
            1,
            min(
                int(target or self.settings.trudvsem_sync_items),
                500,
            ),
        )
        return self.sync_runs.enqueue(
            source=self.source,
            trigger=trigger,
            target=target_value,
            details=details,
        )

    def active_run(self) -> SyncRunRecord | None:
        return self.sync_runs.active(self.source)

    def latest_run(self) -> SyncRunRecord | None:
        return self.sync_runs.latest(self.source)

    def status(self) -> dict[str, object]:
        active = self.active_run()
        latest = self.latest_run()
        target = int((active.target if active else None) or 0)
        processed = int((active.processed if active else None) or 0)
        progress = 0
        if target > 0:
            progress = max(0, min(int(processed * 100 / target), 100))
        return {
            "running": bool(active and active.status == "running"),
            "queued": bool(active and active.status == "queued"),
            "progress_percent": progress,
            "active_run": active,
            "latest_run": latest,
        }

    def recover_stale_runs(self) -> int:
        stale_before = int(time.time()) - self.settings.trudvsem_sync_stale_seconds
        return self.sync_runs.fail_stale(
            self.source,
            stale_before=stale_before,
        )

    def is_due(self) -> bool:
        age = self.vacancy_store.source_age_seconds(self.source)
        return age is None or age >= self.settings.trudvsem_sync_interval

    def run_once(
        self,
        *,
        trigger: str = "scheduled",
        queued_run_id: str | None = None,
        target: int | None = None,
        heartbeat: Callable[[str | None], None] | None = None,
    ) -> SyncExecutionResult:
        """Run one synchronization attempt under a cross-process lock."""

        stale_seconds = self.settings.trudvsem_sync_stale_seconds
        self.recover_stale_runs()
        with SyncExecutionLock(
            self.database,
            source=self.source,
            data_dir=self.settings.data_dir,
            stale_seconds=stale_seconds,
        ) as execution_lock:
            if not execution_lock.acquired:
                active = self.active_run()
                return SyncExecutionResult(
                    status="locked",
                    run=active,
                    processed=int(active.processed if active else 0),
                    saved=int(active.saved if active else 0),
                )

            run = None
            if queued_run_id:
                run = self.sync_runs.claim(queued_run_id)
            if run is None:
                run = self.sync_runs.claim_next(self.source)
            if run is None:
                active = self.active_run()
                if active is not None:
                    return SyncExecutionResult(
                        status="already_running",
                        run=active,
                        processed=active.processed,
                        saved=active.saved,
                    )
                try:
                    run = self.sync_runs.start(
                        source=self.source,
                        trigger=trigger,
                        target=max(
                            1,
                            min(
                                int(target or self.settings.trudvsem_sync_items),
                                500,
                            ),
                        ),
                        details={"execution_mode": "external_worker"},
                    )
                except IntegrityError:
                    active = self.active_run()
                    return SyncExecutionResult(
                        status="already_running",
                        run=active,
                        processed=int(active.processed if active else 0),
                        saved=int(active.saved if active else 0),
                    )

            if heartbeat:
                heartbeat(run.id)
            return self._execute(run, heartbeat=heartbeat)

    def _execute(
        self,
        run: SyncRunRecord,
        *,
        heartbeat: Callable[[str | None], None] | None = None,
    ) -> SyncExecutionResult:
        target = max(1, min(int(run.target or self.settings.trudvsem_sync_items), 500))
        batch_size = max(1, min(self.settings.trudvsem_sync_batch, 10))
        processed = 0
        saved = 0
        error_type = None
        error_message = None

        previous_success = self.sync_runs.latest_succeeded(self.source)
        modified_from = None
        if previous_success and previous_success.finished_at:
            modified_from = datetime.fromtimestamp(
                previous_success.finished_at,
                tz=timezone.utc,
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

        provider = self.provider_factory()
        logger.info(
            "Trudvsem external sync started",
            extra={
                "event": "trudvsem_sync_started",
                "provider": self.source,
                "operation": "external_sync",
                "sync_run_id": run.id,
                "trigger": run.trigger,
                "target": target,
                "incremental": bool(modified_from),
            },
        )

        try:
            total_pages = (target + batch_size - 1) // batch_size
            for page_number in range(1, total_pages + 1):
                if heartbeat:
                    heartbeat(run.id)
                remaining = target - processed
                requested = min(batch_size, remaining)
                with self.provider_operation_factory(
                    self.source,
                    "sync_fetch_batch",
                ) as observation:
                    items = provider.fetch_batch(
                        offset=page_number,
                        limit=requested,
                        modified_from=modified_from,
                    )
                    observation.result_count = len(items)

                if not items:
                    cached_before_sync = self.vacancy_store.count(
                        keyword="",
                        sources=[self.source],
                        period_days=3650,
                    )
                    if (
                        page_number == 1
                        and processed == 0
                        and modified_from is None
                        and cached_before_sync == 0
                    ):
                        raise RuntimeError(
                            "API 'Работы России' вернул пустую первую страницу"
                        )
                    break

                processed += len(items)
                saved += self.vacancy_store.upsert_many(items)
                self.sync_runs.heartbeat(
                    run.id,
                    processed=processed,
                    saved=saved,
                    cursor=str(processed),
                )
                if heartbeat:
                    heartbeat(run.id)
                self.sleeper(0.15)

            finished = self.sync_runs.finish(
                run.id,
                status="succeeded",
                processed=processed,
                saved=saved,
                cursor=str(processed),
                details={
                    "execution_mode": "external_worker",
                    "incremental": bool(modified_from),
                },
            )
            logger.info(
                "Trudvsem external sync completed",
                extra={
                    "event": "trudvsem_sync_completed",
                    "provider": self.source,
                    "operation": "external_sync",
                    "sync_run_id": run.id,
                    "processed": processed,
                    "saved": saved,
                },
            )
            return SyncExecutionResult(
                status="succeeded",
                run=finished,
                processed=processed,
                saved=saved,
            )
        except Exception as exc:
            error_type = type(exc).__name__
            error_message = str(exc)[:500]
            failed = self.sync_runs.finish(
                run.id,
                status="failed",
                processed=processed,
                saved=saved,
                cursor=str(processed),
                error_type=error_type,
                error_message=error_message,
                details={"execution_mode": "external_worker"},
            )
            logger.warning(
                "Trudvsem external sync failed",
                extra={
                    "event": "trudvsem_sync_failed",
                    "provider": self.source,
                    "operation": "external_sync",
                    "sync_run_id": run.id,
                    "error_type": error_type,
                },
            )
            return SyncExecutionResult(
                status="failed",
                run=failed,
                processed=processed,
                saved=saved,
                error_type=error_type,
            )
        finally:
            if heartbeat:
                heartbeat(None)
