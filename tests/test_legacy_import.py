from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import select

from database import create_database
from models import VacancySourceRecord
from repositories import OAuthConnectionRepository


def _create_legacy_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE accounts (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at INTEGER,
                profile_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE hh_accounts (
                user_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at INTEGER,
                profile_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
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
                experience TEXT,
                description TEXT,
                requirements TEXT,
                published_at TEXT,
                url TEXT,
                search_text TEXT,
                raw_json TEXT,
                fetched_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(source, external_id)
            );
            """
        )
        connection.execute(
            "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "SJ", "sj@example.test", "enc-a", "enc-r", 100, "{}", 1),
        )
        connection.execute(
            "INSERT INTO hh_accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("hh-1", "H", "H", "hh@example.test", "enc-a", "enc-r", 100, "{}", 1),
        )
        item = {
            "source": "trudvsem",
            "external_id": "vacancy-1",
            "title": "Imported vacancy",
            "published_at": "2026-08-04T07:00:00Z",
        }
        connection.execute(
            """
            INSERT INTO vacancies (
                source, external_id, title, raw_json, fetched_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "trudvsem",
                "vacancy-1",
                "Imported vacancy",
                json.dumps(item),
                1,
                1,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def test_legacy_import_script_copies_current_tables(tmp_path):
    source = tmp_path / "legacy.db"
    target = tmp_path / "target.db"
    _create_legacy_database(source)

    environment = dict(os.environ)
    environment.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": f"sqlite:///{target.resolve().as_posix()}",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_legacy_sqlite.py",
            "--source",
            str(source),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "superjob_accounts=1" in result.stdout
    assert "hh_accounts=1" in result.stdout
    assert "vacancies=1" in result.stdout

    runtime = create_database(f"sqlite:///{target.resolve().as_posix()}")
    try:
        oauth = OAuthConnectionRepository(runtime)
        assert oauth.get("superjob", "1") is not None
        assert oauth.get("headhunter", "hh-1") is not None
        with runtime.session() as session:
            imported = session.scalar(
                select(VacancySourceRecord).where(
                    VacancySourceRecord.external_id == "vacancy-1"
                )
            )
            assert imported is not None
            assert imported.title == "Imported vacancy"
    finally:
        runtime.dispose()
