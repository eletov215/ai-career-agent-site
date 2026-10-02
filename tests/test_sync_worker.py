from __future__ import annotations

import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from database import create_database, upgrade_database
from services.storage import StorageServices
from services.sync_lock import SyncExecutionLock
from services.trudvsem_sync import TrudvsemSyncService


class _Settings:
    hh_user_agent = "AI-Career-Agent-Test/1.0"
    trudvsem_request_attempts = 1
    trudvsem_retry_backoff = 0.1
    trudvsem_sync_items = 4
    trudvsem_sync_batch = 2
    trudvsem_sync_interval = 1800
    trudvsem_sync_stale_seconds = 120

    def __init__(self, data_dir):
        self.data_dir = data_dir


class _Provider:
    def __init__(self, batches):
        self.batches = list(batches)
        self.calls = []

    def fetch_batch(self, *, offset, limit, modified_from=None):
        self.calls.append(
            {
                "offset": offset,
                "limit": limit,
                "modified_from": modified_from,
            }
        )
        if not self.batches:
            return []
        return self.batches.pop(0)


def _runtime(tmp_path):
    url = f"sqlite:///{(tmp_path / 'sync-worker.db').resolve().as_posix()}"
    upgrade_database(url)
    return create_database(url)


def test_migration_closes_legacy_running_run_before_unique_index(tmp_path):
    url = f"sqlite:///{(tmp_path / 'legacy-running.db').resolve().as_posix()}"
    upgrade_database(url, "20260804_0002")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO sync_runs (
                        id, source, trigger, status, started_at, finished_at,
                        target, processed, saved, cursor, error_type,
                        error_message, details_json, created_at, updated_at
                    ) VALUES (
                        'legacy-run', 'trudvsem', 'background', 'running',
                        1, NULL, 10, 2, 2, '2', NULL, NULL, NULL, 1, 1
                    )
                    """
                )
            )
        upgrade_database(url)
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT status, error_type, finished_at "
                    "FROM sync_runs WHERE id='legacy-run'"
                )
            ).one()
        assert row.status == "failed"
        assert row.error_type == "WorkerRestarted"
        assert row.finished_at is not None
    finally:
        engine.dispose()


def _item(external_id: str, title: str = "Python developer") -> dict:
    return {
        "source": "trudvsem",
        "external_id": external_id,
        "title": title,
        "company": "Example",
        "currency": "RUB",
        "published_at": "2026-08-18T08:00:00Z",
        "url": f"https://example.test/{external_id}",
    }


def test_enqueue_is_durable_and_idempotent(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        storage = StorageServices.from_database(runtime)
        service = TrudvsemSyncService(
            settings=_Settings(tmp_path),
            database=runtime,
            vacancy_store=storage.vacancies,
            sync_runs=storage.sync_runs,
            provider_factory=lambda: _Provider([]),
            sleeper=lambda _seconds: None,
        )

        first = service.enqueue(trigger="test")
        second = service.enqueue(trigger="duplicate")

        assert first.status == "queued"
        assert second.id == first.id
        assert storage.sync_runs.active("trudvsem").id == first.id
    finally:
        runtime.dispose()

    reopened = _runtime(tmp_path)
    try:
        storage = StorageServices.from_database(reopened)
        persisted = storage.sync_runs.active("trudvsem")
        assert persisted is not None
        assert persisted.id == first.id
        assert persisted.status == "queued"
    finally:
        reopened.dispose()


def test_database_enforces_one_active_run_per_source(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        storage = StorageServices.from_database(runtime)
        storage.sync_runs.start(
            source="trudvsem",
            trigger="first",
            target=1,
        )
        with pytest.raises(IntegrityError):
            storage.sync_runs.start(
                source="trudvsem",
                trigger="second",
                target=1,
            )
    finally:
        runtime.dispose()


def test_external_worker_executes_queued_run_and_updates_cache(tmp_path):
    runtime = _runtime(tmp_path)
    provider = _Provider(
        [
            [_item("one"), _item("two")],
            [_item("three")],
        ]
    )
    try:
        storage = StorageServices.from_database(runtime)
        service = TrudvsemSyncService(
            settings=_Settings(tmp_path),
            database=runtime,
            vacancy_store=storage.vacancies,
            sync_runs=storage.sync_runs,
            provider_factory=lambda: provider,
            sleeper=lambda _seconds: None,
            clock=lambda: 1_788_220_800,  # 2026-09-01T00:00:00Z
        )
        queued = service.enqueue(trigger="test")
        heartbeats = []

        result = service.run_once(
            trigger="test-worker",
            queued_run_id=queued.id,
            heartbeat=heartbeats.append,
        )

        assert result.status == "succeeded"
        assert result.processed == 3
        assert result.saved == 3
        # Verify durable cache state directly. The public search count has a
        # rolling seven-day publication filter and must not make this
        # SYNC-001 persistence test expire as the calendar advances.
        assert storage.vacancies.source_status_counts("trudvsem") == {"active": 3}
        latest = storage.sync_runs.latest("trudvsem")
        assert latest.status == "succeeded"
        assert latest.processed == 3
        assert latest.saved == 3
        assert heartbeats[0] == queued.id
        assert heartbeats[-1] is None
    finally:
        runtime.dispose()


def test_failed_external_sync_preserves_existing_cache(tmp_path):
    runtime = _runtime(tmp_path)

    class FailingProvider:
        def fetch_batch(self, **_kwargs):
            raise TimeoutError("private upstream timeout detail")

    try:
        storage = StorageServices.from_database(runtime)
        storage.vacancies.upsert_many([_item("existing")])
        service = TrudvsemSyncService(
            settings=_Settings(tmp_path),
            database=runtime,
            vacancy_store=storage.vacancies,
            sync_runs=storage.sync_runs,
            provider_factory=FailingProvider,
            sleeper=lambda _seconds: None,
        )

        result = service.run_once(trigger="failure-test")

        assert result.status == "failed"
        assert result.error_type == "TimeoutError"
        # A failed refresh must preserve the active cached source row,
        # independent of the UI publication-window filter.
        assert storage.vacancies.source_status_counts("trudvsem") == {"active": 1}
        latest = storage.sync_runs.latest("trudvsem")
        assert latest.status == "failed"
        assert latest.error_type == "TimeoutError"
    finally:
        runtime.dispose()


def test_incremental_sync_uses_latest_success_timestamp(tmp_path):
    runtime = _runtime(tmp_path)
    provider = _Provider([[]])
    try:
        storage = StorageServices.from_database(runtime)
        previous = storage.sync_runs.start(
            source="trudvsem",
            trigger="seed",
            target=1,
        )
        previous = storage.sync_runs.finish(
            previous.id,
            status="succeeded",
            processed=1,
            saved=1,
        )
        service = TrudvsemSyncService(
            settings=_Settings(tmp_path),
            database=runtime,
            vacancy_store=storage.vacancies,
            sync_runs=storage.sync_runs,
            provider_factory=lambda: provider,
            sleeper=lambda _seconds: None,
        )

        result = service.run_once(trigger="incremental-test", target=1)

        assert result.status == "succeeded"
        assert provider.calls[0]["modified_from"] is not None
        assert provider.calls[0]["modified_from"].endswith("Z")
        assert previous.finished_at is not None
    finally:
        runtime.dispose()


def test_stale_running_run_is_closed_before_new_execution(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        storage = StorageServices.from_database(runtime)
        abandoned = storage.sync_runs.start(
            source="trudvsem",
            trigger="abandoned",
            target=1,
        )
        assert storage.sync_runs.fail_stale(
            "trudvsem",
            stale_before=int(time.time()) + 1,
        ) == 1
        closed = storage.sync_runs.latest("trudvsem")
        assert closed is not None
        assert closed.id == abandoned.id
        assert closed.status == "failed"
        assert closed.error_type == "WorkerLost"

        service = TrudvsemSyncService(
            settings=_Settings(tmp_path),
            database=runtime,
            vacancy_store=storage.vacancies,
            sync_runs=storage.sync_runs,
            provider_factory=lambda: _Provider([[_item("replacement")]]),
            sleeper=lambda _seconds: None,
        )
        replacement = service.run_once(trigger="replacement", target=1)
        assert replacement.status == "succeeded"
    finally:
        runtime.dispose()


def test_execution_lock_blocks_parallel_worker(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        storage = StorageServices.from_database(runtime)
        service = TrudvsemSyncService(
            settings=_Settings(tmp_path),
            database=runtime,
            vacancy_store=storage.vacancies,
            sync_runs=storage.sync_runs,
            provider_factory=lambda: _Provider([]),
            sleeper=lambda _seconds: None,
        )
        with SyncExecutionLock(
            runtime,
            source="trudvsem",
            data_dir=tmp_path,
            stale_seconds=120,
        ) as lock:
            assert lock.acquired is True
            result = service.run_once(trigger="parallel-test")
            assert result.status == "locked"
    finally:
        runtime.dispose()


def test_worker_heartbeat_is_persisted_and_pruned(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        storage = StorageServices.from_database(runtime)
        heartbeat = storage.sync_workers.heartbeat(
            worker_id="worker-test",
            source="trudvsem",
            status="idle",
            details={"mode": "test"},
        )
        assert heartbeat.status == "idle"
        assert storage.sync_workers.active(
            "trudvsem",
            stale_after=int(time.time()) - 10,
        )[0].id == "worker-test"

        assert storage.sync_workers.prune_stale(
            stale_before=int(time.time()) + 1
        ) == 1
        assert storage.sync_workers.latest("trudvsem") is None
    finally:
        runtime.dispose()
