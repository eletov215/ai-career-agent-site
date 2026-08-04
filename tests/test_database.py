from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sqlalchemy import inspect, select

from database import (
    INITIAL_REVISION,
    create_database,
    current_revision,
    database_health,
    upgrade_database,
)
from models import Vacancy


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def test_sqlite_migration_is_repeatable_and_health_is_secret_free(tmp_path):
    database_url = sqlite_url(tmp_path / "app.db")

    upgrade_database(database_url)
    upgrade_database(database_url)

    runtime = create_database(database_url)
    try:
        tables = set(inspect(runtime.engine).get_table_names())
        assert {"accounts", "hh_accounts", "vacancies", "alembic_version"} <= tables
        assert current_revision(runtime.engine) == INITIAL_REVISION
        assert database_health(runtime) == {
            "ok": True,
            "backend": "sqlite",
            "persistent": False,
            "revision": INITIAL_REVISION,
        }
    finally:
        runtime.dispose()


def test_postgresql_runtime_is_lazy_and_marked_persistent():
    __import__("pytest").importorskip("psycopg")
    runtime = create_database(
        "postgresql+psycopg://user:secret@example.invalid:5432/career"
    )
    try:
        assert runtime.backend == "postgresql"
        assert runtime.persistent is True
        assert "secret" not in runtime.url.render_as_string(hide_password=True)
    finally:
        runtime.dispose()


def test_initial_migration_adopts_legacy_sqlite_without_losing_rows(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                salary_from REAL,
                salary_to REAL,
                currency TEXT,
                location TEXT,
                remote INTEGER NOT NULL DEFAULT 0,
                schedule TEXT,
                employment TEXT,
                description TEXT,
                requirements TEXT,
                published_at TEXT,
                url TEXT,
                search_text TEXT,
                raw_json TEXT,
                fetched_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(source, external_id)
            )
            """
        )
        raw = {
            "source": "trudvsem",
            "external_id": "legacy-1",
            "title": "Legacy Python role",
            "experience": "Без опыта",
            "published_at": "2026-08-04T10:00:00+03:00",
        }
        connection.execute(
            """
            INSERT INTO vacancies (
                source, external_id, title, raw_json, fetched_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "trudvsem",
                "legacy-1",
                "Legacy Python role",
                json.dumps(raw),
                1,
                1,
            ),
        )
        connection.commit()
    finally:
        connection.close()

    database_url = sqlite_url(path)
    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        with runtime.session() as session:
            vacancy = session.scalar(
                select(Vacancy).where(Vacancy.external_id == "legacy-1")
            )
            assert vacancy is not None
            assert vacancy.experience == "Без опыта"
            assert "legacy python role" in (vacancy.search_text or "")
            assert vacancy.published_at == "2026-08-04T07:00:00Z"
        assert current_revision(runtime.engine) == INITIAL_REVISION
    finally:
        runtime.dispose()
