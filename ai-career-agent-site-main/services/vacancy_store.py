from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable


class VacancyStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vacancies (
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
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vacancies_source_fetched ON vacancies(source, fetched_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vacancies_remote ON vacancies(remote)"
            )
            conn.commit()

    @staticmethod
    def _search_blob(item: dict[str, Any]) -> str:
        values = [
            item.get("title"),
            item.get("company"),
            item.get("location"),
            item.get("description"),
            item.get("requirements"),
        ]
        return " ".join(str(value or "") for value in values).lower()

    def upsert_many(self, items: Iterable[dict[str, Any]]) -> int:
        now = int(time.time())
        rows = []
        for item in items:
            external_id = str(item.get("external_id") or "").strip()
            source = str(item.get("source") or "").strip()
            if not source or not external_id:
                continue
            rows.append(
                (
                    source,
                    external_id,
                    item.get("title") or "Без названия",
                    item.get("company"),
                    item.get("salary_from"),
                    item.get("salary_to"),
                    item.get("currency"),
                    item.get("location"),
                    1 if item.get("remote") else 0,
                    item.get("schedule"),
                    item.get("employment"),
                    item.get("description"),
                    item.get("requirements"),
                    item.get("published_at"),
                    item.get("url"),
                    self._search_blob(item),
                    json.dumps(item, ensure_ascii=False),
                    now,
                    now,
                )
            )
        if not rows:
            return 0

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO vacancies (
                    source, external_id, title, company, salary_from, salary_to,
                    currency, location, remote, schedule, employment, description,
                    requirements, published_at, url, search_text, raw_json,
                    fetched_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, external_id) DO UPDATE SET
                    title=excluded.title,
                    company=excluded.company,
                    salary_from=excluded.salary_from,
                    salary_to=excluded.salary_to,
                    currency=excluded.currency,
                    location=excluded.location,
                    remote=excluded.remote,
                    schedule=excluded.schedule,
                    employment=excluded.employment,
                    description=excluded.description,
                    requirements=excluded.requirements,
                    published_at=excluded.published_at,
                    url=excluded.url,
                    search_text=excluded.search_text,
                    raw_json=excluded.raw_json,
                    fetched_at=excluded.fetched_at,
                    updated_at=excluded.updated_at
                """,
                rows,
            )
            conn.commit()
        return len(rows)

    def search(
        self,
        *,
        keyword: str,
        sources: list[str],
        remote_only: bool = False,
        limit: int = 60,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not sources:
            return []
        placeholders = ",".join("?" for _ in sources)
        terms = [term.lower() for term in keyword.split() if term.strip()]
        conditions = [f"source IN ({placeholders})"]
        params: list[Any] = list(sources)
        for term in terms:
            conditions.append("search_text LIKE ?")
            params.append(f"%{term}%")
        if remote_only:
            conditions.append("remote = 1")
        params.extend([limit, offset])
        sql = f"""
            SELECT raw_json
            FROM vacancies
            WHERE {' AND '.join(conditions)}
            ORDER BY COALESCE(published_at, '') DESC, fetched_at DESC
            LIMIT ? OFFSET ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            try:
                result.append(json.loads(row["raw_json"]))
            except (TypeError, json.JSONDecodeError):
                continue
        return result

    def count(self, *, keyword: str, sources: list[str], remote_only: bool = False) -> int:
        if not sources:
            return 0
        placeholders = ",".join("?" for _ in sources)
        terms = [term.lower() for term in keyword.split() if term.strip()]
        conditions = [f"source IN ({placeholders})"]
        params: list[Any] = list(sources)
        for term in terms:
            conditions.append("search_text LIKE ?")
            params.append(f"%{term}%")
        if remote_only:
            conditions.append("remote = 1")
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) AS total FROM vacancies WHERE {' AND '.join(conditions)}",
                params,
            ).fetchone()
        return int(row["total"] if row else 0)

    def source_age_seconds(self, source: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(fetched_at) AS fetched_at FROM vacancies WHERE source = ?",
                (source,),
            ).fetchone()
        if not row or row["fetched_at"] is None:
            return None
        return max(0, int(time.time()) - int(row["fetched_at"]))
