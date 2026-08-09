from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sqlalchemy import inspect, select, text

from database import (
    CURRENT_REVISION,
    INITIAL_REVISION,
    create_database,
    current_revision,
    database_health,
    upgrade_database,
)
from models import OAuthConnection, Vacancy, VacancySourceRecord


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def test_sqlite_migration_is_repeatable_and_health_is_secret_free(tmp_path):
    database_url = sqlite_url(tmp_path / "app.db")

    upgrade_database(database_url)
    upgrade_database(database_url)

    runtime = create_database(database_url)
    try:
        tables = set(inspect(runtime.engine).get_table_names())
        assert {
            "accounts",
            "hh_accounts",
            "users",
            "oauth_connections",
            "vacancies",
            "vacancy_source_records",
            "sync_runs",
            "search_snapshots",
            "search_snapshot_sources",
            "search_snapshot_candidates",
            "search_snapshot_items",
            "alembic_version",
        } <= tables
        assert current_revision(runtime.engine) == CURRENT_REVISION
        assert database_health(runtime) == {
            "ok": True,
            "backend": "sqlite",
            "persistent": False,
            "revision": CURRENT_REVISION,
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


def test_migrations_adopt_legacy_sqlite_without_losing_vacancy_rows(tmp_path):
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
            source_record = session.scalar(
                select(VacancySourceRecord).where(
                    VacancySourceRecord.external_id == "legacy-1"
                )
            )
            assert source_record is not None
            assert source_record.experience == "Без опыта"
            assert "legacy python role" in (source_record.search_text or "")
            assert source_record.published_at == "2026-08-04T07:00:00Z"
            canonical = session.get(Vacancy, source_record.vacancy_id)
            assert canonical is not None
            assert canonical.title == "Legacy Python role"
            assert canonical.experience == "Без опыта"
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()


def test_domain_migration_copies_legacy_oauth_rows(tmp_path):
    database_url = sqlite_url(tmp_path / "oauth.db")
    upgrade_database(database_url, INITIAL_REVISION)
    runtime = create_database(database_url)
    try:
        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO accounts (
                        user_id, name, email, access_token, refresh_token,
                        expires_at, profile_json, updated_at
                    ) VALUES (1, 'SJ', 'sj@example.test', 'enc-a', 'enc-r', 10, '{}', 5)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO hh_accounts (
                        user_id, first_name, last_name, email, access_token,
                        refresh_token, expires_at, profile_json, updated_at
                    ) VALUES ('hh-1', 'H', 'H', 'hh@example.test', 'enc-a', 'enc-r', 10, '{}', 5)
                    """
                )
            )
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        with runtime.session() as session:
            rows = session.scalars(select(OAuthConnection)).all()
            assert {(row.provider, row.external_user_id) for row in rows} == {
                ("superjob", "1"),
                ("headhunter", "hh-1"),
            }
            assert all(row.user_id is None for row in rows)
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()
