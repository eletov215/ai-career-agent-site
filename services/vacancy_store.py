from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import Engine, and_, case, func, or_, select, tuple_
from sqlalchemy.orm import Session, sessionmaker

from database import DatabaseRuntime, create_database
from models import Vacancy


class VacancyStore:
    """Cross-database vacancy cache backed by SQLAlchemy.

    The constructor keeps the old ``Path`` API used by unit tests, while the
    application passes the shared ``DatabaseRuntime`` created from
    ``DATABASE_URL``.
    """

    def __init__(self, database: DatabaseRuntime | Engine | Path | str):
        self._owned_runtime: DatabaseRuntime | None = None
        if isinstance(database, DatabaseRuntime):
            self.engine = database.engine
            self._sessions = database.session_factory
        elif isinstance(database, Engine):
            self.engine = database
            self._sessions = sessionmaker(
                bind=database,
                autoflush=False,
                expire_on_commit=False,
                future=True,
            )
        else:
            raw = str(database)
            if "://" not in raw:
                path = Path(raw).expanduser().resolve()
                raw = f"sqlite:///{path.as_posix()}"
            runtime = create_database(raw)
            self._owned_runtime = runtime
            self.engine = runtime.engine
            self._sessions = runtime.session_factory

    def init(self) -> None:
        """Create only the vacancy table for isolated compatibility tests."""

        Vacancy.__table__.create(self.engine, checkfirst=True)
        self._backfill_legacy_rows()

    def close(self) -> None:
        if self._owned_runtime is not None:
            self._owned_runtime.dispose()

    def _session(self) -> Session:
        return self._sessions()

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

    @staticmethod
    def _normalize_published_at(value: object | None) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
        else:
            raw = str(value).strip()
            if not raw:
                return None
            if raw.isdigit():
                parsed = datetime.fromtimestamp(float(raw), tz=timezone.utc)
            else:
                try:
                    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    return raw
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                parsed = parsed.astimezone(timezone.utc)
        return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")

    def _backfill_legacy_rows(self) -> None:
        with self._session() as session:
            rows = session.scalars(select(Vacancy)).all()
            changed = False
            for row in rows:
                try:
                    item = json.loads(row.raw_json or "{}")
                except (TypeError, json.JSONDecodeError):
                    item = {}
                if not row.search_text and item:
                    row.search_text = self._search_blob(item)
                    changed = True
                if not row.experience and item.get("experience"):
                    row.experience = item.get("experience")
                    changed = True
                normalized_date = self._normalize_published_at(
                    row.published_at or item.get("published_at")
                )
                if normalized_date != row.published_at:
                    row.published_at = normalized_date
                    changed = True
            if changed:
                session.commit()

    def upsert_many(self, items: Iterable[dict[str, Any]]) -> int:
        now = int(time.time())
        payloads: dict[tuple[str, str], dict[str, Any]] = {}
        for item in items:
            external_id = str(item.get("external_id") or "").strip()
            source = str(item.get("source") or "").strip()
            if not source or not external_id:
                continue
            payloads[(source, external_id)] = {
                "source": source,
                "external_id": external_id,
                "title": item.get("title") or "Без названия",
                "company": item.get("company"),
                "salary_from": item.get("salary_from"),
                "salary_to": item.get("salary_to"),
                "currency": item.get("currency"),
                "location": item.get("location"),
                "remote": bool(item.get("remote")),
                "schedule": item.get("schedule"),
                "employment": item.get("employment"),
                "experience": item.get("experience"),
                "description": item.get("description"),
                "requirements": item.get("requirements"),
                "published_at": self._normalize_published_at(item.get("published_at")),
                "url": item.get("url"),
                "search_text": self._search_blob(item),
                "raw_json": json.dumps(item, ensure_ascii=False),
                "fetched_at": now,
                "updated_at": now,
            }
        if not payloads:
            return 0

        keys = list(payloads)
        with self._session() as session:
            existing = session.scalars(
                select(Vacancy).where(
                    tuple_(Vacancy.source, Vacancy.external_id).in_(keys)
                )
            ).all()
            by_key = {(row.source, row.external_id): row for row in existing}
            for key, values in payloads.items():
                row = by_key.get(key)
                if row is None:
                    session.add(Vacancy(**values))
                    continue
                for name, value in values.items():
                    setattr(row, name, value)
            session.commit()
        return len(payloads)

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
    ) -> list[Any]:
        search_text = func.coalesce(Vacancy.search_text, "")
        conditions: list[Any] = [Vacancy.source.in_(sources)]
        for term in (term.casefold() for term in keyword.split() if term.strip()):
            conditions.append(search_text.like(f"%{term}%"))
        if region:
            conditions.append(search_text.like(f"%{region.casefold()}%"))
        if remote_only or work_format == "remote":
            conditions.append(Vacancy.remote.is_(True))
        elif work_format == "onsite":
            conditions.append(Vacancy.remote.is_(False))
            conditions.append(~search_text.like("%гибк%"))
        elif work_format == "hybrid":
            conditions.append(search_text.like("%гибк%"))
        if currency:
            currency_value = func.upper(func.coalesce(Vacancy.currency, ""))
            currency_code = currency.upper()
            if currency_code == "RUB":
                conditions.append(currency_value.in_(("RUB", "RUR")))
            elif currency_code == "BYN":
                conditions.append(currency_value.in_(("BYN", "BYR")))
            else:
                conditions.append(currency_value == currency_code)
        employment_terms = {
            "full": ("полная", "полный"),
            "part": ("частичная", "неполный"),
            "project": ("проект", "временная"),
            "probation": ("стажиров",),
            "volunteer": ("волонт",),
        }.get(employment, ())
        if employment_terms:
            conditions.append(
                or_(*(search_text.like(f"%{term}%") for term in employment_terms))
            )
        experience_terms = {
            "no_experience": ("без опыта",),
            "between_1_and_3": ("1 год", "1-3", "от 1"),
            "between_3_and_6": ("3 года", "3-6", "от 3"),
            "more_than_6": ("6 лет", "более 6"),
        }.get(experience, ())
        if experience_terms:
            conditions.append(
                or_(*(search_text.like(f"%{term}%") for term in experience_terms))
            )
        if salary_only:
            conditions.append(
                or_(Vacancy.salary_from.is_not(None), Vacancy.salary_to.is_not(None))
            )
        if salary_from is not None:
            conditions.append(
                func.coalesce(Vacancy.salary_to, Vacancy.salary_from, 0) >= salary_from
            )
        if period_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
            cutoff_text = cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")
            conditions.append(Vacancy.published_at >= cutoff_text)
        return conditions

    @staticmethod
    def _order_by(sort: str) -> tuple[Any, ...]:
        published = func.coalesce(Vacancy.published_at, "")
        salary_value = func.coalesce(Vacancy.salary_to, Vacancy.salary_from, 0)
        if sort == "salary_desc":
            return salary_value.desc(), published.desc()
        if sort == "salary_asc":
            missing_salary = case(
                (
                    and_(
                        Vacancy.salary_from.is_(None),
                        Vacancy.salary_to.is_(None),
                    ),
                    1,
                ),
                else_=0,
            )
            return missing_salary.asc(), func.coalesce(
                Vacancy.salary_from,
                Vacancy.salary_to,
                0,
            ).asc(), published.desc()
        return published.desc(), Vacancy.fetched_at.desc()

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
        conditions = self._build_conditions(
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
        statement = (
            select(Vacancy.raw_json)
            .where(*conditions)
            .order_by(*self._order_by(sort))
            .limit(limit)
            .offset(offset)
        )
        with self._session() as session:
            raw_rows = session.scalars(statement).all()
        result: list[dict[str, Any]] = []
        for raw_json in raw_rows:
            try:
                result.append(json.loads(raw_json or "{}"))
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
        conditions = self._build_conditions(
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
        statement = select(func.count(Vacancy.id)).where(*conditions)
        with self._session() as session:
            return int(session.scalar(statement) or 0)

    def source_age_seconds(self, source: str) -> int | None:
        statement = select(func.max(Vacancy.fetched_at)).where(Vacancy.source == source)
        with self._session() as session:
            fetched_at = session.scalar(statement)
        if fetched_at is None:
            return None
        return max(0, int(time.time()) - int(fetched_at))
