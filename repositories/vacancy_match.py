"""Short locked writes; no provider I/O and no profile or vacancy mutations."""
from contextlib import contextmanager
import json
from uuid import uuid4
from sqlalchemy import select, func, text, delete
from .base import RepositoryBase
from models import User
from models.ai import AIUsageEvent
from models.vacancy_match import VacancyMatchReport, VacancyMatchSeries
from domain.vacancy_match import MatchError, MAX_REPORTS_PER_OWNER, MATCH_VERSION
from domain.ai import CONTRACT


def match_view(row):
    """User export omits internal request/accounting identifiers and hashes."""
    return {"id": row.id, "fixture_id": row.fixture_id, "version": row.version,
            "origin": row.origin, "language": row.language, "created_at": row.created_at,
            "source_hash": row.source_hash, "candidate_hash": row.candidate_hash,
            "vacancy_hash": row.vacancy_hash, "result_hash": row.result_hash,
            "source_version": row.source_version, "policy_version": row.policy_version,
            "source_facts": json.loads(row.source_json), "result": json.loads(row.result_json)}


class VacancyMatchRepository(RepositoryBase):
    @contextmanager
    def _write(self, user_id):
        with self.session() as session:
            if self.engine.dialect.name == "sqlite":
                session.execute(text("BEGIN IMMEDIATE"))
            elif self.engine.dialect.name == "postgresql":
                session.execute(text("SET LOCAL lock_timeout = '5s'"))
            owner = session.scalar(select(User).where(User.id == user_id).with_for_update())
            if owner is None or owner.status != "active" or owner.email_verified_at is None:
                raise MatchError("verified_account_required")
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def check_owner(self, user_id, *, room=False):
        with self.session() as session:
            owner = session.get(User, user_id)
            if owner is None or owner.status != "active" or owner.email_verified_at is None:
                raise MatchError("verified_account_required")
            count = session.scalar(select(func.count()).select_from(VacancyMatchReport).where(VacancyMatchReport.user_id == user_id)) if room else 0
            if count >= MAX_REPORTS_PER_OWNER:
                raise MatchError("history_limit")

    def find_operation(self, user_id, operation_hash):
        with self.session() as session:
            row = session.scalar(select(VacancyMatchReport).where(
                VacancyMatchReport.user_id == user_id, VacancyMatchReport.operation_hash == operation_hash))
            return match_view(row) if row else None

    def get(self, user_id, report_id):
        with self.session() as session:
            row = session.scalar(select(VacancyMatchReport).where(VacancyMatchReport.user_id == user_id, VacancyMatchReport.id == report_id))
            return match_view(row) if row else None

    def list(self, user_id):
        with self.session() as session:
            rows = session.scalars(select(VacancyMatchReport).where(VacancyMatchReport.user_id == user_id)
                                   .order_by(VacancyMatchReport.created_at.desc(), VacancyMatchReport.version.desc(), VacancyMatchReport.id)
                                   .limit(MAX_REPORTS_PER_OWNER)).all()
            return [match_view(row) for row in rows]

    def save(self, *, user_id, operation_hash, fixture, source_hash, result, result_hash,
             candidate_hash, vacancy_hash, origin, usage_event_id, now):
        with self._write(user_id) as session:
            existing = session.scalar(select(VacancyMatchReport).where(VacancyMatchReport.user_id == user_id,
                                                                       VacancyMatchReport.operation_hash == operation_hash))
            if existing:
                if (existing.fixture_id, existing.source_hash, existing.origin, existing.policy_version) != (fixture['case_id'], source_hash, origin, MATCH_VERSION):
                    raise MatchError("idempotency_conflict")
                return match_view(existing)
            count = session.scalar(select(func.count()).select_from(VacancyMatchReport).where(VacancyMatchReport.user_id == user_id))
            if count >= MAX_REPORTS_PER_OWNER:
                raise MatchError("history_limit")
            if origin == 'provider':
                usage = session.get(AIUsageEvent, usage_event_id)
                if (usage is None or usage.user_id != user_id or usage.status != 'succeeded'
                        or usage.fixture_id != fixture['case_id'] or usage.task != 'vacancy_match'):
                    raise MatchError('invalid_usage_link')
            elif origin != 'reference' or usage_event_id is not None:
                raise MatchError('invalid_origin')
            series = session.get(VacancyMatchSeries, (user_id, fixture['case_id']))
            if series is None:
                series = VacancyMatchSeries(user_id=user_id, fixture_id=fixture['case_id'], last_version=0)
                session.add(series)
            series.last_version += 1
            row = VacancyMatchReport(id=str(uuid4()), user_id=user_id, fixture_id=fixture['case_id'],
                version=series.last_version, origin=origin, language=fixture['language'], operation_hash=operation_hash,
                source_hash=source_hash, candidate_hash=candidate_hash, vacancy_hash=vacancy_hash, result_hash=result_hash,
                source_version=CONTRACT, policy_version=MATCH_VERSION, usage_event_id=usage_event_id,
                source_json=json.dumps(fixture['source_facts'], ensure_ascii=False, allow_nan=False),
                result_json=json.dumps(result, ensure_ascii=False, allow_nan=False), created_at=now)
            session.add(row)
            session.flush()
            return match_view(row)

    def delete(self, user_id, report_id, result_hash):
        with self._write(user_id) as session:
            row = session.scalar(select(VacancyMatchReport).where(VacancyMatchReport.user_id == user_id,
                                                                VacancyMatchReport.id == report_id))
            if row is None:
                raise MatchError('not_found')
            if row.result_hash != result_hash:
                raise MatchError('stale_report')
            session.execute(delete(VacancyMatchReport).where(VacancyMatchReport.id == report_id,
                                                            VacancyMatchReport.user_id == user_id))
            # The small counter survives report deletion; numbers are not reused.
