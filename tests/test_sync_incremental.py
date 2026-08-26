from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text

from database import create_database, downgrade_database, upgrade_database
from services.storage import StorageServices
from services.trudvsem_provider import TrudvsemBatch, TrudvsemProvider
from services.trudvsem_sync import TrudvsemSyncService


class _Clock:
    def __init__(self, value: int):
        self.value = value

    def __call__(self) -> float:
        return float(self.value)


class _Settings:
    hh_user_agent = "AI-Career-Agent-SYNC002-Test/1.0"
    trudvsem_request_attempts = 1
    trudvsem_retry_backoff = 0.1
    trudvsem_sync_items = 4
    trudvsem_sync_batch = 2
    trudvsem_sync_interval = 1800
    trudvsem_sync_stale_seconds = 120
    trudvsem_sync_watermark_overlap_seconds = 60
    trudvsem_vacancy_ttl_days = 45
    trudvsem_closed_retention_days = 30
    trudvsem_retry_base_seconds = 60
    trudvsem_retry_max_seconds = 3600

    def __init__(self, data_dir):
        self.data_dir = data_dir


class _PagedProvider:
    def __init__(self, pages: dict[int, list[dict]], *, total: int | None):
        self.pages = pages
        self.total = total
        self.calls: list[dict] = []

    def fetch_page(
        self,
        *,
        offset,
        limit,
        modified_from=None,
        modified_to=None,
    ):
        self.calls.append(
            {
                "offset": offset,
                "limit": limit,
                "modified_from": modified_from,
                "modified_to": modified_to,
            }
        )
        return TrudvsemBatch(
            items=list(self.pages.get(offset, [])),
            offset=offset,
            limit=limit,
            total=self.total,
        )


def _runtime(tmp_path, name: str = "sync-002.db"):
    url = f"sqlite:///{(tmp_path / name).resolve().as_posix()}"
    upgrade_database(url)
    return create_database(url)


def _item(
    external_id: str,
    *,
    published_at: str = "2026-08-07T08:00:00Z",
    source_status: str = "active",
    closed_at: int | None = None,
) -> dict:
    return {
        "source": "trudvsem",
        "external_id": external_id,
        "title": f"Vacancy {external_id}",
        "company": "Example",
        "currency": "RUB",
        "published_at": published_at,
        "source_status": source_status,
        "closed_at": closed_at,
        "url": f"https://example.test/{external_id}",
    }


def _seed_checkpoint(storage, *, watermark_at: int, run_id: str = "seed-run"):
    return storage.sync_checkpoints.complete_success(
        "trudvsem",
        run_id=run_id,
        watermark_at=watermark_at,
    )


def _service(tmp_path, runtime, storage, provider, clock):
    return TrudvsemSyncService(
        settings=_Settings(tmp_path),
        database=runtime,
        vacancy_store=storage.vacancies,
        sync_runs=storage.sync_runs,
        sync_checkpoints=storage.sync_checkpoints,
        provider_factory=lambda: provider,
        sleeper=lambda _seconds: None,
        clock=clock,
    )


def test_migration_0004_seeds_checkpoint_and_supports_downgrade(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migration-0004.db').resolve().as_posix()}"
    upgrade_database(url, "20260807_0003")
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
                    ) VALUES
                    (
                        'seed-success-a', 'trudvsem', 'seed', 'succeeded',
                        100, 120, 2, 2, 2, '2', NULL, NULL, NULL, 100, 120
                    ),
                    (
                        'seed-success-z', 'trudvsem', 'seed', 'succeeded',
                        101, 120, 2, 2, 2, '2', NULL, NULL, NULL, 101, 120
                    )
                    """
                )
            )
        upgrade_database(url)
        inspector = inspect(engine)
        assert "sync_checkpoints" in inspector.get_table_names()
        columns = {
            column["name"]
            for column in inspector.get_columns("vacancy_source_records")
        }
        assert {
            "source_modified_at",
            "closed_at",
            "closed_reason",
            "last_seen_run_id",
        } <= columns
        with engine.connect() as connection:
            checkpoint = connection.execute(
                text(
                    "SELECT watermark_at, last_success_run_id "
                    "FROM sync_checkpoints WHERE source='trudvsem'"
                )
            ).one()
        assert checkpoint.watermark_at == 120
        assert checkpoint.last_success_run_id == "seed-success-z"
    finally:
        engine.dispose()

    downgrade_database(url, "20260807_0003")
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert "sync_checkpoints" not in inspector.get_table_names()
        columns = {
            column["name"]
            for column in inspector.get_columns("vacancy_source_records")
        }
        assert "closed_at" not in columns
    finally:
        engine.dispose()


def test_provider_fetch_page_uses_bounded_window_and_maps_lifecycle():
    provider = TrudvsemProvider("test-agent", request_attempts=1)
    captured = {}

    def fake_request(params):
        captured.update(params)
        return {
            "status": "200",
            "meta": {"total": "2"},
            "results": {
                "vacancies": [
                    {
                        "vacancy": {
                            "id": "active-1",
                            "job-name": "Active vacancy",
                            "creation-date": "2026-08-07T08:00:00Z",
                            "modified-date": "2026-08-07T09:00:00Z",
                        }
                    },
                    {
                        "vacancy": {
                            "id": "closed-1",
                            "job-name": "Closed vacancy",
                            "creation-date": "2026-08-01T08:00:00Z",
                            "status": "closed",
                        }
                    },
                ]
            },
        }

    provider._request = fake_request  # type: ignore[method-assign]
    batch = provider.fetch_page(
        offset=2,
        limit=10,
        modified_from="2026-08-07T08:00:00Z",
        modified_to="2026-08-07T10:00:00Z",
    )

    assert captured["offset"] == 2
    assert captured["limit"] == 10
    assert captured["modifiedFrom"] == "2026-08-07T08:00:00Z"
    assert captured["modifiedTo"] == "2026-08-07T10:00:00Z"
    assert batch.total == 2
    assert batch.items[0]["source_status"] == "active"
    assert batch.items[0]["source_modified_at"] == "2026-08-07T09:00:00Z"
    assert batch.items[1]["source_status"] == "closed"
    assert batch.items[1]["closed_reason"] == "provider_status"


def test_incremental_window_uses_overlap_and_advances_watermark(tmp_path):
    runtime = _runtime(tmp_path)
    clock = _Clock(2_000)
    provider = _PagedProvider(
        {1: [_item("one"), _item("two")]},
        total=2,
    )
    try:
        storage = StorageServices.from_database(runtime)
        _seed_checkpoint(storage, watermark_at=1_000)
        service = _service(tmp_path, runtime, storage, provider, clock)

        result = service.run_once(trigger="manual-cli")

        assert result.status == "succeeded"
        assert result.mode == "incremental"
        assert result.window_complete is True
        assert provider.calls[0]["modified_from"] == "1970-01-01T00:15:40Z"
        assert provider.calls[0]["modified_to"] == "1970-01-01T00:33:20Z"
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert checkpoint is not None
        assert checkpoint.watermark_at == 2_000
        assert checkpoint.has_pending_window is False
        latest = storage.sync_runs.latest("trudvsem")
        cursor = json.loads(latest.cursor)
        assert cursor["window_complete"] is True
        assert cursor["next_offset"] == 2
    finally:
        runtime.dispose()


def test_initial_recent_window_is_resumable_and_becomes_watermark(tmp_path):
    runtime = _runtime(tmp_path)
    clock = _Clock(4_000_000)
    pages = {
        1: [_item("bootstrap-1"), _item("bootstrap-2")],
        2: [_item("bootstrap-3"), _item("bootstrap-4")],
        3: [_item("bootstrap-5"), _item("bootstrap-6")],
    }
    provider = _PagedProvider(pages, total=6)
    try:
        storage = StorageServices.from_database(runtime)
        service = _service(tmp_path, runtime, storage, provider, clock)

        first = service.run_once(trigger="manual-cli")
        assert first.mode == "initial"
        assert first.window_complete is False
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert checkpoint is not None
        assert checkpoint.watermark_at is None
        assert checkpoint.pending_offset == 3
        assert checkpoint.pending_from_at == max(
            0,
            4_000_000 - _Settings.trudvsem_vacancy_ttl_days * 86_400,
        )
        assert provider.calls[0]["modified_to"] == "1970-02-16T07:06:40Z"

        second = service.run_once(trigger="manual-cli")
        assert second.mode == "initial"
        assert second.window_complete is True
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert checkpoint.watermark_at == 4_000_000
        assert checkpoint.has_pending_window is False
        assert [call["offset"] for call in provider.calls] == [1, 2, 3]
        assert storage.vacancies.repository.source_record_count() == 6
    finally:
        runtime.dispose()


def test_incremental_cursor_continues_across_runs_without_duplicates(tmp_path):
    runtime = _runtime(tmp_path)
    clock = _Clock(2_000)
    pages = {
        1: [_item("1"), _item("2")],
        2: [_item("3"), _item("4")],
        3: [_item("5"), _item("6")],
        4: [_item("7"), _item("8")],
    }
    provider = _PagedProvider(pages, total=8)
    try:
        storage = StorageServices.from_database(runtime)
        _seed_checkpoint(storage, watermark_at=1_000)
        service = _service(tmp_path, runtime, storage, provider, clock)

        first = service.run_once(trigger="manual-cli")
        assert first.window_complete is False
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert checkpoint.watermark_at == 1_000
        assert checkpoint.pending_offset == 3
        assert storage.vacancies.count(
            keyword="",
            sources=["trudvsem"],
            period_days=0,
        ) == 4

        second = service.run_once(trigger="manual-cli")
        assert second.window_complete is True
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert checkpoint.watermark_at == 2_000
        assert checkpoint.has_pending_window is False
        assert [call["offset"] for call in provider.calls] == [1, 2, 3, 4]
        assert storage.vacancies.count(
            keyword="",
            sources=["trudvsem"],
            period_days=0,
        ) == 8

        # Replaying the same records is an idempotent upsert, not duplication.
        storage.vacancies.upsert_many(pages[1])
        assert storage.vacancies.repository.source_record_count() == 8
    finally:
        runtime.dispose()


def test_pending_cursor_survives_database_reconnect(tmp_path):
    database_path = (tmp_path / "reconnect.db").resolve()
    database_url = f"sqlite:///{database_path.as_posix()}"
    upgrade_database(database_url)
    clock = _Clock(2_000)
    provider = _PagedProvider(
        {
            1: [_item("reconnect-1"), _item("reconnect-2")],
            2: [_item("reconnect-3"), _item("reconnect-4")],
            3: [_item("reconnect-5"), _item("reconnect-6")],
        },
        total=6,
    )

    runtime = create_database(database_url)
    storage = StorageServices.from_database(runtime)
    _seed_checkpoint(storage, watermark_at=1_000)
    service = _service(tmp_path, runtime, storage, provider, clock)
    first = service.run_once(trigger="manual-cli")
    assert first.window_complete is False
    assert storage.sync_checkpoints.get("trudvsem").pending_offset == 3
    runtime.dispose()

    runtime = create_database(database_url)
    try:
        storage = StorageServices.from_database(runtime)
        service = _service(tmp_path, runtime, storage, provider, clock)
        second = service.run_once(trigger="manual-cli")
        assert second.window_complete is True
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert checkpoint.watermark_at == 2_000
        assert checkpoint.has_pending_window is False
        assert [call["offset"] for call in provider.calls] == [1, 2, 3]
        assert storage.vacancies.repository.source_record_count() == 6
    finally:
        runtime.dispose()


def test_failure_keeps_watermark_and_sets_exponential_retry(tmp_path):
    runtime = _runtime(tmp_path)
    clock = _Clock(2_000)

    class FailingProvider:
        def fetch_page(self, **_kwargs):
            raise TimeoutError("upstream unavailable")

    try:
        storage = StorageServices.from_database(runtime)
        _seed_checkpoint(storage, watermark_at=1_000)
        service = _service(
            tmp_path,
            runtime,
            storage,
            FailingProvider(),
            clock,
        )

        first = service.run_once(trigger="manual-cli")
        assert first.status == "failed"
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert checkpoint.watermark_at == 1_000
        assert checkpoint.pending_offset == 1
        assert checkpoint.consecutive_failures == 1
        assert checkpoint.next_retry_at == 2_060
        assert service.is_due() is False

        clock.value = 2_061
        assert service.is_due() is True
        second = service.run_once(trigger="manual-cli")
        checkpoint = storage.sync_checkpoints.get("trudvsem")
        assert second.status == "failed"
        assert checkpoint.consecutive_failures == 2
        assert checkpoint.next_retry_at == 2_181
    finally:
        runtime.dispose()


def test_closed_records_are_hidden_ttl_cleaned_and_reactivated(tmp_path):
    runtime = _runtime(tmp_path)
    now = int(
        datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc).timestamp()
    )
    try:
        storage = StorageServices.from_database(runtime)
        storage.vacancies.upsert_many(
            [
                _item("recent", published_at="2026-08-01T08:00:00Z"),
                _item("old", published_at="2026-05-01T08:00:00Z"),
                _item(
                    "provider-closed",
                    published_at="2026-08-01T08:00:00Z",
                    source_status="closed",
                    closed_at=now - 40 * 86_400,
                ),
            ],
            seen_at=now,
        )
        assert storage.vacancies.count(
            keyword="",
            sources=["trudvsem"],
            period_days=0,
        ) == 2

        cleanup = storage.vacancies.cleanup_source(
            source="trudvsem",
            vacancy_ttl_days=45,
            closed_retention_days=30,
            now=now,
        )
        assert cleanup.closed == 1
        assert cleanup.purged == 1
        assert storage.vacancies.count(
            keyword="",
            sources=["trudvsem"],
            period_days=0,
        ) == 1
        old = storage.vacancies.repository.get_source("trudvsem", "old")
        assert old.source_status == "closed"
        assert old.closed_reason == "published_ttl"
        assert storage.vacancies.repository.get_source(
            "trudvsem", "provider-closed"
        ) is None

        storage.vacancies.upsert_many(
            [_item("old", published_at="2026-08-07T08:00:00Z")],
            seen_at=now + 1,
        )
        old = storage.vacancies.repository.get_source("trudvsem", "old")
        assert old.source_status == "active"
        assert old.closed_at is None
        assert storage.vacancies.count(
            keyword="",
            sources=["trudvsem"],
            period_days=0,
        ) == 2
    finally:
        runtime.dispose()
