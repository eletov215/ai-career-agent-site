#!/usr/bin/env python3
"""Import a legacy app.db snapshot into the configured database.

OAuth rows are copied into the unified DATA-002 ``oauth_connections`` table.
Tokens remain encrypted and require the same ``TOKEN_ENCRYPTION_KEY`` in the
target environment.  Vacancy cache rows are normalized through VacancyStore.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_database_url  # noqa: E402
from database import create_database, upgrade_database  # noqa: E402
from repositories import OAuthConnectionRepository  # noqa: E402
from services.vacancy_store import VacancyStore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Path to legacy app.db")
    return parser.parse_args()


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def main() -> int:
    args = parse_args()
    source_path = args.source.expanduser().resolve()
    if not source_path.is_file():
        print(f"Legacy SQLite file not found: {source_path}", file=sys.stderr)
        return 2

    database_url, _explicit = load_database_url()
    target = create_database(database_url)
    if target.backend == "sqlite" and Path(target.url.database or "").resolve() == source_path:
        print("Source and target SQLite database are the same file.", file=sys.stderr)
        target.dispose()
        return 2

    upgrade_database(database_url)
    oauth_repository = OAuthConnectionRepository(target)
    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    imported_superjob = 0
    imported_hh = 0
    vacancy_items: list[dict[str, object]] = []
    try:
        if table_exists(source, "accounts"):
            for row in source.execute("SELECT * FROM accounts"):
                oauth_repository.upsert(
                    provider="superjob",
                    external_user_id=str(row["user_id"]),
                    display_name=row["name"],
                    email=row["email"],
                    access_token=row["access_token"],
                    refresh_token=row["refresh_token"],
                    expires_at=row["expires_at"],
                    profile_json=row["profile_json"],
                    updated_at=row["updated_at"],
                )
                imported_superjob += 1
        if table_exists(source, "hh_accounts"):
            for row in source.execute("SELECT * FROM hh_accounts"):
                display_name = " ".join(
                    part for part in (row["first_name"], row["last_name"]) if part
                ) or None
                oauth_repository.upsert(
                    provider="headhunter",
                    external_user_id=str(row["user_id"]),
                    display_name=display_name,
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    email=row["email"],
                    access_token=row["access_token"],
                    refresh_token=row["refresh_token"],
                    expires_at=row["expires_at"],
                    profile_json=row["profile_json"],
                    updated_at=row["updated_at"],
                )
                imported_hh += 1

        if table_exists(source, "vacancies"):
            for row in source.execute("SELECT raw_json FROM vacancies"):
                try:
                    item = json.loads(row["raw_json"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(item, dict):
                    vacancy_items.append(item)
        imported_vacancies = VacancyStore(target).upsert_many(vacancy_items)
    finally:
        source.close()
        target.dispose()

    print(
        "Legacy import complete: "
        f"superjob_accounts={imported_superjob}, "
        f"hh_accounts={imported_hh}, vacancies={imported_vacancies}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
