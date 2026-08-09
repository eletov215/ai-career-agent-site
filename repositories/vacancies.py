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
            dedup_key=row.dedup_key,
            dedup_version=row.dedup_version,
            title=row.title,
            company=row.company,
            salary_from=row.salary_from,
            salary_to=row.salary_to,
            currency=row.currency,
            location=row.location,
            remote=bool(row.remote),
            work_format=row.work_format,
            employment_code=row.employment_code,
            experience_code=row.experience_code,
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
            dedup_key=row.dedup_key,
            dedup_version=row.dedup_version,
            title=row.title,
            company=row.company,
            salary_from=row.salary_from,
            salary_to=row.salary_to,
            currency=row.currency,
            location=row.location,
            remote=bool(row.remote),
            work_format=row.work_format,
            employment_code=row.employment_code,
            experience_code=row.experience_code,
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


    def list_sources_by_dedup_keys(self, dedup_keys: Iterable[str]) -> list[SourceRecord]:
        keys = sorted({str(key).strip() for key in dedup_keys if str(key).strip()})
        if not keys:
            return []
        with self.session() as session:
            rows = session.scalars(
                select(VacancySourceRecord)
                .where(
                    VacancySourceRecord.dedup_key.in_(keys),
                    VacancySourceRecord.source_status == "active",
                )
                .order_by(
                    VacancySourceRecord.dedup_key,
                    VacancySourceRecord.first_seen_at,
                    VacancySourceRecord.id,
                )
            ).all()
            return [self._source_record(row) for row in rows]

    def merge_source_record_group(
        self,
        *,
        source_keys: Iterable[tuple[str, str]],
        canonical_values: dict[str, Any],
        dedup_key: str | None,
        dedup_version: int | None,
    ) -> str | None:
        """Attach proven duplicate source rows to one canonical vacancy.

        SEARCH-002 performs the decision outside the repository.  This method
        only applies that explicit group and removes canonicals that become
        orphaned after reassignment.
        """

        keys = sorted(
            {
                (str(source).strip(), str(external_id).strip())
                for source, external_id in source_keys
                if str(source).strip() and str(external_id).strip()
            }
        )
        if len(keys) < 2:
            return None
        now = int(time.time())
        with self.session() as session:
            rows = session.scalars(
                select(VacancySourceRecord)
                .where(
                    tuple_(
                        VacancySourceRecord.source,
                        VacancySourceRecord.external_id,
                    ).in_(keys)
                )
                .order_by(VacancySourceRecord.first_seen_at, VacancySourceRecord.id)
            ).all()
            if len(rows) < 2 or len({row.source for row in rows}) < 2:
                return None

            canonical_rows = {
                row.vacancy_id: session.get(Vacancy, row.vacancy_id)
                for row in rows
            }
            target = min(
                (row for row in rows if canonical_rows.get(row.vacancy_id) is not None),
                key=lambda row: (
                    canonical_rows[row.vacancy_id].created_at,
                    row.first_seen_at,
                    row.id,
                ),
                default=None,
            )
            if target is None:
                return None
            target_id = target.vacancy_id
            target_canonical = canonical_rows[target_id]
            old_ids = {row.vacancy_id for row in rows if row.vacancy_id != target_id}
            for row in rows:
                row.vacancy_id = target_id
                row.dedup_key = dedup_key
                row.dedup_version = dedup_version

            values = dict(canonical_values)
            values["dedup_key"] = dedup_key
            values["dedup_version"] = dedup_version
            for name, value in self._canonical_values(values, now=now).items():
                setattr(target_canonical, name, value)
            target_canonical.dedup_key = dedup_key
            target_canonical.dedup_version = dedup_version

            session.flush()
            if old_ids:
                session.execute(
                    delete(Vacancy).where(
                        Vacancy.id.in_(old_ids),
                        ~exists(
                            select(VacancySourceRecord.id).where(
                                VacancySourceRecord.vacancy_id == Vacancy.id
                            )
                        ),
                    )
                )
            self._refresh_canonical_activity(session, {target_id, *old_ids})
            session.commit()
            return target_id

    @staticmethod
    def _canonical_values(values: dict[str, Any], *, now: int) -> dict[str, Any]:
        return {
            "dedup_key": values.get("dedup_key"),
            "dedup_version": values.get("dedup_version"),
            "title": values["title"],
            "company": values.get("company"),
            "salary_from": values.get("salary_from"),
            "salary_to": values.get("salary_to"),
            "currency": values.get("currency"),
            "location": values.get("location"),
            "remote": bool(values.get("remote")),
            "work_format": values.get("work_format"),
            "employment_code": values.get("employment_code"),
            "experience_code": values.get("experience_code"),
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
    def _source_row_values(row: VacancySourceRecord) -> dict[str, Any]:
        return {
            "dedup_key": row.dedup_key,
            "dedup_version": row.dedup_version,
            "title": row.title,
            "company": row.company,
            "salary_from": row.salary_from,
            "salary_to": row.salary_to,
            "currency": row.currency,
            "location": row.location,
            "remote": bool(row.remote),
            "work_format": row.work_format,
            "employment_code": row.employment_code,
            "experience_code": row.experience_code,
            "schedule": row.schedule,
            "employment": row.employment,
            "experience": row.experience,
            "description": row.description,
            "requirements": row.requirements,
            "published_at": row.published_at,
            "source_status": row.source_status,
        }

    @staticmethod
    def _source_row_score(row: VacancySourceRecord) -> tuple[int, int, str, str]:
        score = 0
        score += 3 if str(row.url or "").strip() else 0
        score += 2 if row.salary_from is not None or row.salary_to is not None else 0
        score += 1 if str(row.company or "").strip() else 0
        score += 1 if str(row.location or "").strip() else 0
        score += min(len(str(row.description or "")) // 180, 3)
        score += min(len(str(row.requirements or "")) // 120, 2)
        score += sum(
            1
            for value in (row.work_format, row.employment_code, row.experience_code)
            if value not in (None, "", "unknown")
        )
        return score, int(row.last_seen_at or 0), row.source, row.external_id

    @classmethod
    def _merged_values_from_source_rows(
        cls,
        rows: list[VacancySourceRecord],
    ) -> dict[str, Any]:
        representative = max(rows, key=cls._source_row_score)
        values = cls._source_row_values(representative)
        fill_fields = (
            "company",
            "salary_from",
            "salary_to",
            "currency",
            "location",
            "work_format",
            "employment_code",
            "experience_code",
            "schedule",
            "employment",
            "experience",
        )
        ordered = sorted(rows, key=cls._source_row_score, reverse=True)
        for field in fill_fields:
            if values.get(field) not in (None, "", "unknown"):
                continue
            for row in ordered:
                candidate = getattr(row, field)
                if candidate not in (None, "", "unknown"):
                    values[field] = candidate
                    break
        for field in ("description", "requirements"):
            values[field] = max(
                (str(getattr(row, field) or "") for row in rows),
                key=len,
                default="",
            )
        published = [str(row.published_at) for row in rows if row.published_at]
        values["published_at"] = max(published, default=None)
        values["source_status"] = (
            "active" if any(row.source_status == "active" for row in rows) else "closed"
        )
        active_keys = {
            row.dedup_key
            for row in rows
            if row.source_status == "active" and row.dedup_key
        }
        if len(active_keys) == 1:
            values["dedup_key"] = next(iter(active_keys))
            values["dedup_version"] = max(
                (int(row.dedup_version or 0) for row in rows),
                default=0,
            ) or None
        else:
            values["dedup_key"] = None
            values["dedup_version"] = None
        return values

    def detach_source_record(
        self,
        *,
        source: str,
        external_id: str,
        canonical_values: dict[str, Any],
        dedup_key: str | None,
        dedup_version: int | None,
    ) -> str | None:
        """Detach one changed publication from a previously merged canonical.

        The operation makes SEARCH-002 grouping reversible.  Source rows are
        never deleted; when a publication no longer matches every other active
        member, it receives its own canonical vacancy before the update is
        applied.
        """

        now = int(time.time())
        source = str(source).strip()
        external_id = str(external_id).strip()
        if not source or not external_id:
            return None
        with self.session() as session:
            row = session.scalar(
                select(VacancySourceRecord).where(
                    VacancySourceRecord.source == source,
                    VacancySourceRecord.external_id == external_id,
                )
            )
            if row is None:
                return None
            source_count = int(
                session.scalar(
                    select(func.count(VacancySourceRecord.id)).where(
                        VacancySourceRecord.vacancy_id == row.vacancy_id
                    )
                )
                or 0
            )
            if source_count <= 1:
                return row.vacancy_id

            previous_id = row.vacancy_id
            new_id = str(uuid.uuid4())
            values = dict(canonical_values)
            values["dedup_key"] = dedup_key
            values["dedup_version"] = dedup_version
            new_canonical = Vacancy(
                id=new_id,
                fingerprint=(
                    f"source:{source}:{external_id}:split:{uuid.uuid4().hex[:12]}"
                ),
                created_at=now,
                **self._canonical_values(values, now=now),
            )
            session.add(new_canonical)
            session.flush()
            row.vacancy_id = new_id
            row.dedup_key = dedup_key
            row.dedup_version = dedup_version
            session.flush()

            remaining = session.scalars(
                select(VacancySourceRecord)
                .where(VacancySourceRecord.vacancy_id == previous_id)
                .order_by(VacancySourceRecord.first_seen_at, VacancySourceRecord.id)
            ).all()
            previous = session.get(Vacancy, previous_id)
            if previous is not None and remaining:
                rebuilt = self._merged_values_from_source_rows(list(remaining))
                for name, value in self._canonical_values(rebuilt, now=now).items():
                    setattr(previous, name, value)
                previous.dedup_key = rebuilt.get("dedup_key")
                previous.dedup_version = rebuilt.get("dedup_version")

            self._refresh_canonical_activity(session, {previous_id, new_id})
            session.commit()
            return new_id

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
        selected_work_format = "remote" if remote_only else work_format
        if selected_work_format:
            legacy_work_format = {
                "remote": record.remote.is_(True),
                "onsite": and_(
                    record.remote.is_(False),
                    ~search_text.like("%гибк%"),
                    ~search_text.like("%hybrid%"),
                ),
                "hybrid": or_(
                    search_text.like("%гибк%"),
                    search_text.like("%hybrid%"),
                ),
            }.get(selected_work_format)
            if legacy_work_format is not None:
                conditions.append(
                    or_(
                        record.work_format == selected_work_format,
                        and_(record.work_format.is_(None), legacy_work_format),
                    )
                )
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
            "project": ("проект", "контракт", "временная"),
            "probation": ("стажиров",),
            "volunteer": ("волонт",),
        }.get(employment, ())
        if employment_terms:
            legacy_employment = or_(
                *(search_text.like(f"%{term}%") for term in employment_terms)
            )
            conditions.append(
                or_(
                    record.employment_code == employment,
                    and_(record.employment_code.is_(None), legacy_employment),
                )
            )
        experience_terms = {
            "no_experience": ("без опыта",),
            "between_1_and_3": ("1 год", "1-3", "от 1"),
            "between_3_and_6": ("3 года", "3-6", "от 3"),
            "more_than_6": ("6 лет", "более 6"),
        }.get(experience, ())
        if experience_terms:
            legacy_experience = or_(
                *(search_text.like(f"%{term}%") for term in experience_terms)
            )
            conditions.append(
                or_(
                    record.experience_code == experience,
                    and_(record.experience_code.is_(None), legacy_experience),
                )
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
