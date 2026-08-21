from __future__ import annotations

import pytest


def test_search005_model_is_registered():
    from models import Base

    table = Base.metadata.tables["source_health_states"]
    assert table.c.provider.primary_key
    assert "availability" in table.c
    assert "configured" in table.c
    assert "last_latency_ms" in table.c
    assert "error_code" in table.c


def test_search005_migration_round_trip(tmp_path):
    pytest.importorskip("alembic")
    from config import load_database_url
    from database import current_revision, create_database, downgrade_database, upgrade_database

    database_url = f"sqlite:///{(tmp_path / 'search005.db').as_posix()}"
    upgrade_database(database_url, "20260819_0014")
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == "20260819_0014"
        with runtime.engine.connect() as connection:
            tables = set(__import__("sqlalchemy").inspect(connection).get_table_names())
            assert "source_health_states" in tables
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260813_0013")
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == "20260813_0013"
        with runtime.engine.connect() as connection:
            tables = set(__import__("sqlalchemy").inspect(connection).get_table_names())
            assert "source_health_states" not in tables
            assert "privacy_audit_events" in tables
    finally:
        runtime.dispose()

    upgrade_database(database_url, "20260819_0014")
