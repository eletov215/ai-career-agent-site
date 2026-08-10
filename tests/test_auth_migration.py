from __future__ import annotations

from sqlalchemy import inspect

from database import CURRENT_REVISION, create_database, current_revision, downgrade_database, upgrade_database


def test_auth_0008_migration_round_trip(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'auth-migration.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        tables = set(inspector.get_table_names())
        assert {"auth_sessions", "auth_tokens"} <= tables
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        assert {"password_hash", "password_changed_at", "last_login_at"} <= user_columns
        assert current_revision(runtime.engine) == "20260810_0008"
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260809_0007")
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        tables = set(inspector.get_table_names())
        assert "auth_sessions" not in tables
        assert "auth_tokens" not in tables
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        assert "password_hash" not in user_columns
        assert current_revision(runtime.engine) == "20260809_0007"
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()
