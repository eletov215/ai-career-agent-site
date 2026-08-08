"""Repository for canonical vacancies and provider source records."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import and_, case, delete, exists, func, or_, select, tuple_, update

from domain import SourceRecord, VacancyRecord
from models import Vacancy, VacancySourceRecord

from .base import RepositoryBase


class VacancyRepository(RepositoryBase):
    """Encapsulate all SQLAlchemy vacancy queries used by the application."""

    def init_schema(self) -> None:
        Vacancy.__table__.create(self.engine, checkfirst=True)
        VacancySourceRecord.__table__.create(self.engine, checkfirst=True)

    @staticmethod
    def _vacancy_record(row: Vacancy) -> VacancyRecord:
        return VacancyRecord(
            id=row.id,
            fingerprint=row.fingerprint,
            title=row.title,
            company=row.company,
            salary_from=row.salary_from,
            salary_to=row.salary_to,
            currency=row.currency,
            location=row.location,
            remote=bool(row.remote),
            schedule=row.schedule,
            employment=row.employment,
            experience=row.experience,
            description=row.description,
            requirements=row.requirements,
            published_at=row.published_at,
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _source_record(row: VacancySourceRecord) -> SourceRecord:
        return SourceRecord(
            id=row.id,
            vacancy_id=row.vacancy_id,
            source=row.source,
            external_id=row.external_id,
            title=row.title,
            company=row.company,
            salary_from=row.salary_from,
            salary_to=row.salary_to,
            currency=row.currency,
            location=row.location,
            remote=bool(row.remote),
            schedule=row.schedule,
            employment=row.employment,
            experience=row.experience,
            description=row.description,
            requirements=row.requirements,
            published_at=row.published_at,
            url=row.url,
            search_text=row.search_text,
            raw_json=row.raw_json,
            source_status=row.source_status,
            source_modified_at=row.source_modified_at,
            closed_at=row.closed_at,
            closed_reason=row.closed_reason,
            last_seen_run_id=row.last_seen_run_id,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            fetched_at=row.fetched_at,
            updated_at=row.updated_at,
        )

    def get_canonical(self, vacancy_id: str) -> VacancyRecord | None:
        with self.session() as session:
            row = session.get(Vacancy, vacancy_id)
            return self._vacancy_record(row) if row else None

    def get_source(self, source: str, external_id: str) -> SourceRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(VacancySourceRecord).where(
                    VacancySourceRecord.source == source.strip(),
                    VacancySourceRecord.external_id == str(external_id).strip(),
                )
            )
            return self._source_record(row) if row else None

    def list_sources(self, vacancy_id: str) -> list[SourceRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(VacancySourceRecord)
                .where(VacancySourceRecord.vacancy_id == vacancy_id)
                .order_by(VacancySourceRecord.source, VacancySourceRecord.external_id)
            ).all()
            return [self._source_record(row) for row in rows]

    @staticmethod
    def _canonical_values(values: dict[str, Any], *, now: int) -> dict[str, Any]:
        return {
            "title": values["title"],
            "company": values.get("company"),
            "salary_from": values.get("salary_from"),
            "salary_to": values.get("salary_to"),
            "currency": values.get("currency"),
            "location": values.get("location"),
            "remote": bool(values.get("remote")),
            "schedule": values.get("schedule"),
            "employment": values.get("employment"),
            "experience": values.get("experience"),
            "description": values.get("description"),
            "requirements": values.get("requirements"),
            "published_at": values.get("published_at"),
            "is_active": values.get("source_status", "active") == "active",
            "updated_at": now,
        }

    @staticmethod
    def _refresh_canonical_activity(session, vacancy_ids: set[str]) -> None:  # noqa: ANN001
        for vacancy_id in vacancy_ids:
            canonical = session.get(Vacancy, vacancy_id)
            if canonical is None:
                continue
            active_count = session.scalar(
                select(func.count(VacancySourceRecord.id)).where(
                    VacancySourceRecord.vacancy_id == vacancy_id,
                    VacancySourceRecord.source_status == "active",
                )
            )
            canonical.is_active = bool(active_count)

    def upsert_source_records(self, payloads: Iterable[dict[str, Any]]) -> int:
        rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for values in payloads:
            source = str(values.get("source") or "").strip()
            external_id = str(values.get("external_id") or "").strip()
            if source and external_id:
                rows_by_key[(source, external_id)] = dict(values)
        if not rows_by_key:
            return 0

        keys = list(rows_by_key)
        now = int(time.time())
        touched_vacancy_ids: set[str] = set()
        with self.session() as session:
            existing = session.scalars(
                select(VacancySourceRecord).where(
                    tuple_(
                        VacancySourceRecord.source,
                        VacancySourceRecord.external_id,
                    ).in_(keys)
                )
            ).all()
            by_key = {(row.source, row.external_id): row for row in existing}

            for key, values in rows_by_key.items():
                source_status = str(values.get("source_status") or "active").strip().lower()
                if source_status not in {"active", "closed"}:
                    source_status = "active"
                values["source_status"] = source_status
                if source_status == "active":
                    values["closed_at"] = None
                    values["closed_reason"] = None
                else:
                    values["closed_at"] = int(values.get("closed_at") or now)
                    values["closed_reason"] = str(
                        values.get("closed_reason") or "provider_status"
                    )[:64]

                source_record = by_key.get(key)
                if source_record is None:
                    canonical_id = str(uuid.uuid4())
                    canonical = Vacancy(
                        id=canonical_id,
                        fingerprint=f"source:{key[0]}:{key[1]}",
                        created_at=now,
                        **self._canonical_values(values, now=now),
                    )
                    session.add(canonical)
                    record_values = dict(values)
                    source_status_value = record_values.pop("source_status", "active")
                    first_seen_at = record_values.pop(
                        "first_seen_at",
                        record_values.get("fetched_at", now),
                    )
                    last_seen_at = record_values.pop(
                        "last_seen_at",
                        record_values.get("updated_at", now),
                    )
                    source_record = VacancySourceRecord(
                        vacancy_id=canonical_id,
                        source_status=source_status_value,
                        first_seen_at=first_seen_at,
                        last_seen_at=last_seen_at,
                        **record_values,
                    )
                    session.add(source_record)
                    touched_vacancy_ids.add(canonical_id)
                    continue

                source_record.last_seen_at = int(
                    values.get("last_seen_at")
                    or values.get("updated_at")
                    or now
                )
                for name, value in values.items():
                    if hasattr(source_record, name):
                        setattr(source_record, name, value)

                canonical = session.get(Vacancy, source_record.vacancy_id)
                if canonical is None:
                    canonical = Vacancy(
                        id=source_record.vacancy_id,
                        fingerprint=f"source:{key[0]}:{key[1]}",
                        created_at=now,
                        **self._canonical_values(values, now=now),
                    )
                    session.add(canonical)
                else:
                    for name, value in self._canonical_values(values, now=now).items():
                        setattr(canonical, name, value)
                touched_vacancy_ids.add(source_record.vacancy_id)

            session.flush()
            self._refresh_canonical_activity(session, touched_vacancy_ids)
            session.commit()
        return len(rows_by_key)

    def mark_expired_active(
        self,
        *,
        source: str,
        published_before: str,
        closed_at: int,
        reason: str = "published_ttl",
    ) -> int:
        """Hide active records older than the supported search window."""

        with self.session() as session:
            vacancy_ids = set(
                session.scalars(
                    select(VacancySourceRecord.vacancy_id).where(
                        VacancySourceRecord.source == source,
                        VacancySourceRecord.source_status == "active",
                        VacancySourceRecord.published_at.is_not(None),
                        VacancySourceRecord.published_at < published_before,
                    )
                ).all()
            )
            if not vacancy_ids:
                return 0
            result = session.execute(
                update(VacancySourceRecord)
                .where(
                    VacancySourceRecord.source == source,
                    VacancySourceRecord.source_status == "active",
                    VacancySourceRecord.published_at.is_not(None),
                    VacancySourceRecord.published_at < published_before,
                )
                .values(
                    source_status="closed",
                    closed_at=int(closed_at),
                    closed_reason=str(reason)[:64],
                    updated_at=int(closed_at),
                )
            )
            session.flush()
            self._refresh_canonical_activity(session, vacancy_ids)
            session.commit()
            return int(result.rowcount or 0)

    def purge_closed(
        self,
        *,
        source: str,
        closed_before: int,
    ) -> int:
        """Delete long-retained closed source rows and orphan canonicals."""

        with self.session() as session:
            rows = session.execute(
                select(
                    VacancySourceRecord.id,
                    VacancySourceRecord.vacancy_id,
                ).where(
                    VacancySourceRecord.source == source,
                    VacancySourceRecord.source_status == "closed",
                    VacancySourceRecord.closed_at.is_not(None),
                    VacancySourceRecord.closed_at < int(closed_before),
                )
            ).all()
            if not rows:
                return 0
            row_ids = [row.id for row in rows]
            vacancy_ids = {row.vacancy_id for row in rows}
            result = session.execute(
                delete(VacancySourceRecord).where(
                    VacancySourceRecord.id.in_(row_ids)
                )
            )
            session.flush()
            session.execute(
                delete(Vacancy).where(
                    Vacancy.id.in_(vacancy_ids),
                    ~exists(
                        select(VacancySourceRecord.id).where(
                            VacancySourceRecord.vacancy_id == Vacancy.id
                        )
                    ),
                )
            )
            self._refresh_canonical_activity(session, vacancy_ids)
            session.commit()
            return int(result.rowcount or 0)

    def source_status_counts(self, source: str) -> dict[str, int]:
        with self.session() as session:
            rows = session.execute(
                select(
                    VacancySourceRecord.source_status,
                    func.count(VacancySourceRecord.id),
                )
                .where(VacancySourceRecord.source == source)
                .group_by(VacancySourceRecord.source_status)
            ).all()
        return {str(status): int(count) for status, count in rows}

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
        record = VacancySourceRecord
        search_text = func.coalesce(record.search_text, "")
        conditions: list[Any] = [record.source.in_(sources)]
        for term in (term.casefold() for term in keyword.split() if term.strip()):
            conditions.append(search_text.like(f"%{term}%"))
        if region:
            conditions.append(search_text.like(f"%{region.casefold()}%"))
        if remote_only or work_format == "remote":
            conditions.append(record.remote.is_(True))
        elif work_format == "onsite":
            conditions.append(record.remote.is_(False))
            conditions.append(~search_text.like("%гибк%"))
        elif work_format == "hybrid":
            conditions.append(search_text.like("%гибк%"))
        if currency:
            currency_value = func.upper(func.coalesce(record.currency, ""))
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
                or_(record.salary_from.is_not(None), record.salary_to.is_not(None))
            )
        if salary_from is not None:
            conditions.append(
                func.coalesce(record.salary_to, record.salary_from, 0) >= salary_from
            )
        if period_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
            cutoff_text = cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")
            conditions.append(record.published_at >= cutoff_text)
        conditions.append(record.source_status == "active")
        return conditions

    @staticmethod
    def _order_by(sort: str) -> tuple[Any, ...]:
        record = VacancySourceRecord
        published = func.coalesce(record.published_at, "")
        salary_value = func.coalesce(record.salary_to, record.salary_from, 0)
        if sort == "salary_desc":
            return salary_value.desc(), published.desc()
        if sort == "salary_asc":
            missing_salary = case(
                ((and_(record.salary_from.is_(None), record.salary_to.is_(None)), 1)),
                else_=0,
            )
            return (
                missing_salary.asc(),
                func.coalesce(record.salary_from, record.salary_to, 0).asc(),
                published.desc(),
            )
        return published.desc(), record.fetched_at.desc()

    def search_raw_json(
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
    ) -> list[str | None]:
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
            select(VacancySourceRecord.raw_json)
            .where(*conditions)
            .order_by(*self._order_by(sort))
            .limit(limit)
            .offset(offset)
        )
        with self.session() as session:
            return list(session.scalars(statement).all())

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
        with self.session() as session:
            return int(
                session.scalar(
                    select(func.count(VacancySourceRecord.id)).where(*conditions)
                )
                or 0
            )

    def source_age_seconds(self, source: str) -> int | None:
        with self.session() as session:
            fetched_at = session.scalar(
                select(func.max(VacancySourceRecord.fetched_at)).where(
                    VacancySourceRecord.source == source,
                    VacancySourceRecord.source_status == "active",
                )
            )
        if fetched_at is None:
            return None
        return max(0, int(time.time()) - int(fetched_at))

    def canonical_count(self) -> int:
        with self.session() as session:
            return int(session.scalar(select(func.count(Vacancy.id))) or 0)

    def source_record_count(self) -> int:
        with self.session() as session:
            return int(session.scalar(select(func.count(VacancySourceRecord.id))) or 0)
