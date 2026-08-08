"""Hosting-independent Trudvsem incremental synchronization service."""

from __future__ import annotations

import json
import logging
import math
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, ContextManager, Protocol

from sqlalchemy.exc import IntegrityError

from config import AppSettings
from database import DatabaseRuntime
from domain import SyncCheckpointRecord, SyncRunRecord
from repositories import SyncCheckpointRepository, SyncRunRepository
from services.sync_lock import SyncExecutionLock
from services.trudvsem_provider import TrudvsemBatch, TrudvsemProvider
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
def _noop_provider_operation(_provider: str, _operation: str):
    yield _NoopProviderObservation()


@dataclass(frozen=True, slots=True)
class SyncExecutionResult:
    """Sanitized result returned to CLI/worker callers."""

    status: str
    run: SyncRunRecord | None
    processed: int = 0
    saved: int = 0
    closed: int = 0
    purged: int = 0
    error_type: str | None = None
    mode: str | None = None
    window_complete: bool = True
    next_retry_at: int | None = None

    @property
    def ok(self) -> bool:
        return self.status in {
            "succeeded",
            "already_running",
            "locked",
            "backoff",
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "status": self.status,
            "run_id": self.run.id if self.run else None,
            "source": self.run.source if self.run else "trudvsem",
            "trigger": self.run.trigger if self.run else None,
            "processed": self.processed,
            "saved": self.saved,
            "closed": self.closed,
            "purged": self.purged,
            "mode": self.mode,
            "window_complete": self.window_complete,
            "next_retry_at": self.next_retry_at,
            "error_type": self.error_type,
        }


class TrudvsemSyncService:
    """Execute resumable Trudvsem synchronization outside Flask."""

    source = "trudvsem"
    _MANUAL_TRIGGERS = {
        "api",
        "manual-cli",
        "development-refresh",
        "test",
        "test-worker",
    }

    def __init__(
        self,
        *,
        settings: AppSettings,
        database: DatabaseRuntime,
        vacancy_store: VacancyStore,
        sync_runs: SyncRunRepository,
        sync_checkpoints: SyncCheckpointRepository | None = None,
        provider_factory: Callable[[], TrudvsemProvider] | None = None,
        provider_operation_factory: ProviderOperationFactory | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.settings = settings
        self.database = database
        self.vacancy_store = vacancy_store
        self.sync_runs = sync_runs
        self.sync_checkpoints = sync_checkpoints or SyncCheckpointRepository(database)
        self.provider_factory = provider_factory or self._default_provider
        self.provider_operation_factory = (
            provider_operation_factory or _noop_provider_operation
        )
        self.sleeper = sleeper
        self.clock = clock

    def _setting(self, name: str, default: int) -> int:
        return int(getattr(self.settings, name, default))

    def _default_provider(self) -> TrudvsemProvider:
        return TrudvsemProvider(
            self.settings.hh_user_agent,
            per_page=10,
            timeout=(5, 45),
            scan_pages=5,
            request_attempts=self.settings.trudvsem_request_attempts,
            retry_backoff=self.settings.trudvsem_retry_backoff,
        )

    @staticmethod
    def _format_timestamp(value: int | None) -> str | None:
        if value is None:
            return None
        return datetime.fromtimestamp(
            int(value),
            tz=timezone.utc,
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

    def enqueue(
        self,
        *,
        trigger: str,
        target: int | None = None,
        details: dict[str, object] | None = None,
    ) -> SyncRunRecord:
        target_value = max(
            1,
            min(int(target or self.settings.trudvsem_sync_items), 500),
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

    def checkpoint(self) -> SyncCheckpointRecord:
        return self.sync_checkpoints.ensure(self.source)

    def status(self) -> dict[str, object]:
        active = self.active_run()
        latest = self.latest_run()
        checkpoint = self.sync_checkpoints.get(self.source)
        target = int((active.target if active else None) or 0)
        processed = int((active.processed if active else None) or 0)
        progress = 0
        if target > 0:
            progress = max(0, min(int(processed * 100 / target), 100))
        counts = self.vacancy_store.source_status_counts(self.source)
        return {
            "running": bool(active and active.status == "running"),
            "queued": bool(active and active.status == "queued"),
            "progress_percent": progress,
            "active_run": active,
            "latest_run": latest,
            "checkpoint": checkpoint,
            "active_total": int(counts.get("active", 0)),
            "closed_total": int(counts.get("closed", 0)),
            "retry_pending": bool(
                checkpoint
                and checkpoint.next_retry_at
                and checkpoint.next_retry_at > int(self.clock())
            ),
        }

    def recover_stale_runs(self) -> int:
        stale_before = int(self.clock()) - self.settings.trudvsem_sync_stale_seconds
        return self.sync_runs.fail_stale(
            self.source,
            stale_before=stale_before,
        )

    def retry_due(self) -> bool:
        return self.sync_checkpoints.retry_due(
            self.source,
            now=int(self.clock()),
        )

    def is_due(self) -> bool:
        checkpoint = self.sync_checkpoints.get(self.source)
        if checkpoint and checkpoint.has_pending_window:
            return self.retry_due()
        if not self.retry_due():
            return False
        age = self.vacancy_store.source_age_seconds(self.source)
        if age is None and checkpoint and checkpoint.last_success_at:
            age = max(0, int(self.clock()) - int(checkpoint.last_success_at))
        return age is None or age >= self.settings.trudvsem_sync_interval

    def should_run(self, active: SyncRunRecord | None = None) -> bool:
        if active is not None and active.status == "queued":
            if active.trigger in self._MANUAL_TRIGGERS:
                return True
            return self.retry_due()
        return self.is_due()

    def run_once(
        self,
        *,
        trigger: str = "scheduled",
        queued_run_id: str | None = None,
        target: int | None = None,
        heartbeat: Callable[[str | None], None] | None = None,
    ) -> SyncExecutionResult:
        """Run one resumable synchronization chunk under a process lock."""

        active_before = self.active_run()
        automatic_trigger = trigger in {
            "scheduled",
            "scheduled-worker",
            "cache-miss",
            "web",
        }
        if automatic_trigger and not self.should_run(active_before):
            checkpoint = self.sync_checkpoints.get(self.source)
            return SyncExecutionResult(
                status="backoff",
                run=active_before,
                processed=int(active_before.processed if active_before else 0),
                saved=int(active_before.saved if active_before else 0),
                next_retry_at=(checkpoint.next_retry_at if checkpoint else None),
            )

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

    def _fetch_page(
        self,
        provider: TrudvsemProvider,
        *,
        offset: int,
        limit: int,
        modified_from: str | None,
        modified_to: str | None,
    ) -> TrudvsemBatch:
        fetch_page = getattr(provider, "fetch_page", None)
        if callable(fetch_page):
            return fetch_page(
                offset=offset,
                limit=limit,
                modified_from=modified_from,
                modified_to=modified_to,
            )
        try:
            items = provider.fetch_batch(
                offset=offset,
                limit=limit,
                modified_from=modified_from,
                modified_to=modified_to,
            )
        except TypeError:
            items = provider.fetch_batch(
                offset=offset,
                limit=limit,
                modified_from=modified_from,
            )
        return TrudvsemBatch(
            items=list(items),
            offset=offset,
            limit=limit,
            total=None,
        )

    def _prepare_window(
        self,
        *,
        batch_size: int,
    ) -> tuple[str, SyncCheckpointRecord, int, int | None, int | None]:
        checkpoint = self.checkpoint()
        if checkpoint.watermark_at is None:
            if checkpoint.has_pending_window:
                return (
                    "initial",
                    checkpoint,
                    int(checkpoint.pending_offset or 1),
                    checkpoint.pending_from_at,
                    checkpoint.pending_to_at,
                )
            previous_success = self.sync_runs.latest_succeeded(self.source)
            if previous_success and previous_success.finished_at:
                checkpoint = self.sync_checkpoints.complete_success(
                    self.source,
                    run_id=previous_success.id,
                    watermark_at=int(previous_success.finished_at),
                    clear_pending=False,
                )
            else:
                window_to = int(self.clock())
                lookback_days = self._setting(
                    "trudvsem_vacancy_ttl_days",
                    45,
                )
                window_from = max(0, window_to - lookback_days * 86_400)
                checkpoint = self.sync_checkpoints.begin_window(
                    self.source,
                    from_at=window_from,
                    to_at=window_to,
                    offset=1,
                    limit=batch_size,
                )
                return "initial", checkpoint, 1, window_from, window_to
        if checkpoint.has_pending_window:
            return (
                "incremental",
                checkpoint,
                int(checkpoint.pending_offset or 1),
                checkpoint.pending_from_at,
                checkpoint.pending_to_at,
            )

        overlap = self._setting(
            "trudvsem_sync_watermark_overlap_seconds",
            300,
        )
        window_to = int(self.clock())
        window_from = max(0, int(checkpoint.watermark_at) - overlap)
        checkpoint = self.sync_checkpoints.begin_window(
            self.source,
            from_at=window_from,
            to_at=window_to,
            offset=1,
            limit=batch_size,
        )
        return "incremental", checkpoint, 1, window_from, window_to

    @staticmethod
    def _cursor_json(
        *,
        mode: str,
        offset: int,
        next_offset: int,
        total: int | None,
        modified_from: str | None,
        modified_to: str | None,
        window_complete: bool,
    ) -> str:
        return json.dumps(
            {
                "mode": mode,
                "offset": offset,
                "next_offset": next_offset,
                "total": total,
                "modified_from": modified_from,
                "modified_to": modified_to,
                "window_complete": window_complete,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def _execute(
        self,
        run: SyncRunRecord,
        *,
        heartbeat: Callable[[str | None], None] | None = None,
    ) -> SyncExecutionResult:
        max_items = max(
            1,
            min(int(run.target or self.settings.trudvsem_sync_items), 500),
        )
        batch_size = max(1, min(self.settings.trudvsem_sync_batch, 10))
        max_pages = max(1, math.ceil(max_items / batch_size))
        processed = 0
        saved = 0
        closed = 0
        purged = 0
        error_type = None

        mode, checkpoint, offset, window_from, window_to = self._prepare_window(
            batch_size=batch_size
        )
        if mode == "incremental" and checkpoint.pending_limit:
            batch_size = int(checkpoint.pending_limit)
            max_pages = max(1, math.ceil(max_items / batch_size))
        modified_from = self._format_timestamp(window_from)
        modified_to = self._format_timestamp(window_to)

        provider = self.provider_factory()
        logger.info(
            "Trudvsem incremental sync started",
            extra={
                "event": "trudvsem_sync_started",
                "provider": self.source,
                "operation": "external_sync",
                "sync_run_id": run.id,
                "trigger": run.trigger,
                "target": max_items,
                "sync_mode": mode,
                "offset": offset,
                "modified_from": modified_from,
                "modified_to": modified_to,
            },
        )

        window_complete = False
        total: int | None = checkpoint.pending_total
        next_offset = offset
        cursor = None
        try:
            for _page_index in range(max_pages):
                if heartbeat:
                    heartbeat(run.id)
                with self.provider_operation_factory(
                    self.source,
                    "sync_fetch_page",
                ) as observation:
                    batch = self._fetch_page(
                        provider,
                        offset=next_offset,
                        limit=batch_size,
                        modified_from=modified_from,
                        modified_to=modified_to,
                    )
                    observation.result_count = batch.returned

                if total is None and batch.total is not None:
                    total = batch.total
                    if mode in {"initial", "incremental"}:
                        self.sync_checkpoints.advance_window(
                            self.source,
                            next_offset=next_offset,
                            total=total,
                        )
                    already_before = max(0, (next_offset - 1) * batch_size)
                    expected_this_run = max(
                        0,
                        min(max_items, max(0, total - already_before)),
                    )
                    self.sync_runs.set_target(
                        run.id,
                        target=expected_this_run,
                    )

                if not batch.items:
                    if mode == "initial" and next_offset == 1:
                        cached_before_sync = self.vacancy_store.count(
                            keyword="",
                            sources=[self.source],
                            period_days=3650,
                        )
                        if cached_before_sync == 0:
                            raise RuntimeError(
                                "API 'Работы России' вернул пустую первую страницу"
                            )
                    window_complete = True
                    break

                seen_at = int(self.clock())
                processed += batch.returned
                saved += self.vacancy_store.upsert_many(
                    batch.items,
                    run_id=run.id,
                    seen_at=seen_at,
                )
                page_offset = next_offset
                next_offset += 1
                if mode in {"initial", "incremental"}:
                    self.sync_checkpoints.advance_window(
                        self.source,
                        next_offset=next_offset,
                        total=total,
                    )

                window_complete = batch.exhausted
                cursor = self._cursor_json(
                    mode=mode,
                    offset=page_offset,
                    next_offset=next_offset,
                    total=total,
                    modified_from=modified_from,
                    modified_to=modified_to,
                    window_complete=window_complete,
                )
                self.sync_runs.heartbeat(
                    run.id,
                    processed=processed,
                    saved=saved,
                    cursor=cursor,
                )
                if heartbeat:
                    heartbeat(run.id)
                if window_complete:
                    break
                self.sleeper(0.15)

            cleanup_at = int(self.clock())
            cleanup = None
            if window_complete:
                cleanup = self.vacancy_store.cleanup_source(
                    source=self.source,
                    vacancy_ttl_days=self._setting(
                        "trudvsem_vacancy_ttl_days",
                        45,
                    ),
                    closed_retention_days=self._setting(
                        "trudvsem_closed_retention_days",
                        30,
                    ),
                    now=cleanup_at,
                )
                closed = cleanup.closed
                purged = cleanup.purged
                self.sync_checkpoints.complete_success(
                    self.source,
                    run_id=run.id,
                    watermark_at=int(window_to or cleanup_at),
                    cleanup_at=cleanup_at,
                    clear_pending=True,
                )
            else:
                self.sync_checkpoints.record_partial_success(
                    self.source,
                    run_id=run.id,
                )

            details = {
                "execution_mode": "external_worker",
                "sync_mode": mode,
                "window_complete": window_complete,
                "modified_from": modified_from,
                "modified_to": modified_to,
                "next_offset": next_offset,
                "total": total,
                "cleanup": cleanup.as_dict() if cleanup else None,
            }
            finished = self.sync_runs.finish(
                run.id,
                status="succeeded",
                processed=processed,
                saved=saved,
                cursor=cursor,
                details=details,
            )
            logger.info(
                "Trudvsem incremental sync completed",
                extra={
                    "event": "trudvsem_sync_completed",
                    "provider": self.source,
                    "operation": "external_sync",
                    "sync_run_id": run.id,
                    "processed": processed,
                    "saved": saved,
                    "closed": closed,
                    "purged": purged,
                    "sync_mode": mode,
                    "window_complete": window_complete,
                    "next_offset": next_offset,
                    "total": total,
                },
            )
            return SyncExecutionResult(
                status="succeeded",
                run=finished,
                processed=processed,
                saved=saved,
                closed=closed,
                purged=purged,
                mode=mode,
                window_complete=window_complete,
            )
        except Exception as exc:
            error_type = type(exc).__name__
            error_message = str(exc)[:500]
            checkpoint = self.sync_checkpoints.record_failure(
                self.source,
                base_seconds=self._setting(
                    "trudvsem_retry_base_seconds",
                    60,
                ),
                max_seconds=max(
                    self._setting("trudvsem_retry_base_seconds", 60),
                    self._setting("trudvsem_retry_max_seconds", 3600),
                ),
                now=int(self.clock()),
            )
            failed = self.sync_runs.finish(
                run.id,
                status="failed",
                processed=processed,
                saved=saved,
                cursor=cursor,
                error_type=error_type,
                error_message=error_message,
                details={
                    "execution_mode": "external_worker",
                    "sync_mode": mode,
                    "window_complete": False,
                    "next_retry_at": checkpoint.next_retry_at,
                },
            )
            logger.warning(
                "Trudvsem incremental sync failed",
                extra={
                    "event": "trudvsem_sync_failed",
                    "provider": self.source,
                    "operation": "external_sync",
                    "sync_run_id": run.id,
                    "error_type": error_type,
                    "next_retry_at": checkpoint.next_retry_at,
                    "consecutive_failures": checkpoint.consecutive_failures,
                },
            )
            return SyncExecutionResult(
                status="failed",
                run=failed,
                processed=processed,
                saved=saved,
                error_type=error_type,
                mode=mode,
                window_complete=False,
                next_retry_at=checkpoint.next_retry_at,
            )
        finally:
            if heartbeat:
                heartbeat(None)
