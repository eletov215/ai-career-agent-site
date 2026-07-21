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
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
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
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vacancies_source_fetched ON vacancies(source, fetched_at DESC)"
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(vacancies)").fetchall()}
            if "experience" not in columns:
                conn.execute("ALTER TABLE vacancies ADD COLUMN experience TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vacancies_remote ON vacancies(remote)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_vacancies_location ON vacancies(location)"
            )
            stale_rows = conn.execute("SELECT id, raw_json FROM vacancies").fetchall()
            for row in stale_rows:
                try:
                    item = json.loads(row["raw_json"])
                except (TypeError, json.JSONDecodeError):
                    continue
                conn.execute(
                    "UPDATE vacancies SET search_text = ?, experience = COALESCE(experience, ?) WHERE id = ?",
                    (self._search_blob(item), item.get("experience"), row["id"]),
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
            item.get("schedule"),
            item.get("employment"),
            item.get("experience"),
            item.get("currency"),
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
                    item.get("experience"),
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
                    currency, location, remote, schedule, employment, experience, description,
                    requirements, published_at, url, search_text, raw_json,
                    fetched_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    experience=excluded.experience,
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

    @staticmethod
    def _build_conditions(
        *,
        keyword: str,
        sources: list[str],
        remote_only: bool,
        salary_from: int | None,
        salary_only: bool,
        period_days: int,
        region: str = "",
        experience: str = "",
        employment: str = "",
        work_format: str = "",
        currency: str = "",
    ) -> tuple[list[str], list[Any]]:
        placeholders = ",".join("?" for _ in sources)
        terms = [term.lower() for term in keyword.split() if term.strip()]
        conditions = [f"source IN ({placeholders})"]
        params: list[Any] = list(sources)
        for term in terms:
            conditions.append("search_text LIKE ?")
            params.append(f"%{term}%")
        if region:
            conditions.append("search_text LIKE ?")
            params.append(f"%{region.casefold()}%")
        if remote_only or work_format == "remote":
            conditions.append("remote = 1")
        elif work_format == "onsite":
            conditions.append("remote = 0")
            conditions.append("search_text NOT LIKE '%гибк%'")
        elif work_format == "hybrid":
            conditions.append("search_text LIKE '%гибк%'")
        if currency:
            if currency.upper() == "RUB":
                conditions.append("UPPER(COALESCE(currency, '')) IN ('RUB', 'RUR')")
            else:
                conditions.append("UPPER(COALESCE(currency, '')) = ?")
                params.append(currency.upper())
        employment_terms = {
            "full": ("полная", "полный"),
            "part": ("частичная", "неполный"),
            "project": ("проект", "временная"),
            "probation": ("стажиров",),
            "volunteer": ("волонт",),
        }.get(employment, ())
        if employment_terms:
            conditions.append("(" + " OR ".join("search_text LIKE ?" for _ in employment_terms) + ")")
            params.extend(f"%{term}%" for term in employment_terms)
        experience_terms = {
            "no_experience": ("без опыта",),
            "between_1_and_3": ("1 год", "1-3", "от 1"),
            "between_3_and_6": ("3 года", "3-6", "от 3"),
            "more_than_6": ("6 лет", "более 6"),
        }.get(experience, ())
        if experience_terms:
            conditions.append("(" + " OR ".join("search_text LIKE ?" for _ in experience_terms) + ")")
            params.extend(f"%{term}%" for term in experience_terms)
        if salary_only:
            conditions.append("(salary_from IS NOT NULL OR salary_to IS NOT NULL)")
        if salary_from is not None:
            conditions.append("COALESCE(salary_to, salary_from, 0) >= ?")
            params.append(salary_from)
        if period_days > 0:
            conditions.append("datetime(published_at) >= datetime('now', ?)")
            params.append(f"-{period_days} days")
        return conditions, params

    def search(
        self,
        *,
        keyword: str,
        sources: list[str],
        remote_only: bool = False,
        salary_from: int | None = None,
        salary_only: bool = False,
        period_days: int = 7,
        sort: str = "date",
        limit: int = 60,
        offset: int = 0,
        region: str = "",
        experience: str = "",
        employment: str = "",
        work_format: str = "",
        currency: str = "",
    ) -> list[dict[str, Any]]:
        if not sources:
            return []
        conditions, params = self._build_conditions(
            keyword=keyword,
            sources=sources,
            remote_only=remote_only,
            salary_from=salary_from,
            salary_only=salary_only,
            period_days=period_days,
            region=region,
            experience=experience,
            employment=employment,
            work_format=work_format,
            currency=currency,
        )
        order_by = {
            "salary_desc": "COALESCE(salary_to, salary_from, 0) DESC, COALESCE(published_at, '') DESC",
            "salary_asc": "CASE WHEN salary_from IS NULL AND salary_to IS NULL THEN 1 ELSE 0 END, COALESCE(salary_from, salary_to, 0) ASC, COALESCE(published_at, '') DESC",
            "relevance": "COALESCE(published_at, '') DESC, fetched_at DESC",
            "date": "COALESCE(published_at, '') DESC, fetched_at DESC",
        }.get(sort, "COALESCE(published_at, '') DESC, fetched_at DESC")
        params.extend([limit, offset])
        sql = f"""
            SELECT raw_json
            FROM vacancies
            WHERE {' AND '.join(conditions)}
            ORDER BY {order_by}
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

    def count(
        self,
        *,
        keyword: str,
        sources: list[str],
        remote_only: bool = False,
        salary_from: int | None = None,
        salary_only: bool = False,
        period_days: int = 7,
        region: str = "",
        experience: str = "",
        employment: str = "",
        work_format: str = "",
        currency: str = "",
    ) -> int:
        if not sources:
            return 0
        conditions, params = self._build_conditions(
            keyword=keyword,
            sources=sources,
            remote_only=remote_only,
            salary_from=salary_from,
            salary_only=salary_only,
            period_days=period_days,
            region=region,
            experience=experience,
            employment=employment,
            work_format=work_format,
            currency=currency,
        )
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
