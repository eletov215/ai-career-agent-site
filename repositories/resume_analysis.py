"""AI-002 owner isolation and short transactions; never call a provider here."""
from contextlib import contextmanager
import json
from uuid import uuid4
from sqlalchemy import select, func, text, delete
from models import User
from models.ai import AIUsageEvent
from models.resume_analysis import ResumeAnalysisReport, ResumeAnalysisDecision, ResumeAnalysisReviewEvent
from domain.resume_analysis import AnalysisError, MAX_REPORTS_PER_OWNER, ANALYSIS_VERSION
from .base import RepositoryBase

def report_view(row, decisions=(), events=()):
    """No operation hashes or credentials in user-facing output."""
    return {
        "id": row.id, "fixture_id": row.fixture_id, "source_hash": row.source_hash,
        "source_version": row.source_version, "analysis_version": row.analysis_version,
        "version": row.version, "language": row.language, "origin": row.origin,
        "created_at": row.created_at, "source_facts": json.loads(row.source_json),
        "result": json.loads(row.result_json),
        "decisions": {r.recommendation_id: {"decision": r.decision, "revision": r.revision} for r in decisions},
        "review_events": [{"recommendation_id": e.recommendation_id, "decision": e.decision,
                           "revision": e.revision, "created_at": e.created_at} for e in events],
    }

class ResumeAnalysisRepository(RepositoryBase):
    @contextmanager
    def _write(self, user_id):
        with self.session() as s:
            if self.engine.dialect.name == "sqlite":
                s.execute(text("BEGIN IMMEDIATE"))
            stmt = select(User).where(User.id == user_id).with_for_update()
            owner = s.scalar(stmt)
            if owner is None or owner.status != "active" or owner.email_verified_at is None:
                raise AnalysisError("verified_account_required")
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    def _view(self, s, row):
        ds = s.scalars(select(ResumeAnalysisDecision).where(ResumeAnalysisDecision.report_id == row.id)).all()
        es = s.scalars(select(ResumeAnalysisReviewEvent).where(ResumeAnalysisReviewEvent.report_id == row.id)
                       .order_by(ResumeAnalysisReviewEvent.created_at, ResumeAnalysisReviewEvent.revision)).all()
        return report_view(row, ds, es)

    def check_owner(self, user_id, room=False):
        with self.session() as s:
            u=s.get(User,user_id)
            if u is None or u.status!='active' or u.email_verified_at is None:
                raise AnalysisError('verified_account_required')
            if room and s.scalar(select(func.count()).select_from(ResumeAnalysisReport).where(ResumeAnalysisReport.user_id==user_id)) >= MAX_REPORTS_PER_OWNER:
                raise AnalysisError('history_limit')

    def find_operation(self, user_id, operation_hash):
        with self.session() as s:
            row = s.scalar(select(ResumeAnalysisReport).where(ResumeAnalysisReport.user_id == user_id,
                                                          ResumeAnalysisReport.operation_hash == operation_hash))
            return self._view(s, row) if row else None

    def get(self, user_id, report_id):
        with self.session() as s:
            row = s.scalar(select(ResumeAnalysisReport).where(ResumeAnalysisReport.user_id == user_id, ResumeAnalysisReport.id == report_id))
            return self._view(s, row) if row else None

    def list(self, user_id, limit=50):
        with self.session() as s:
            rows = s.scalars(select(ResumeAnalysisReport).where(ResumeAnalysisReport.user_id == user_id)
                             .order_by(ResumeAnalysisReport.created_at.desc(), ResumeAnalysisReport.id.desc()).limit(max(1, min(limit, 100)))).all()
            return [{"id": r.id, "fixture_id": r.fixture_id, "version": r.version, "origin": r.origin,
                     "language": r.language, "created_at": r.created_at} for r in rows]

    def save(self, *, user_id, operation_hash, fixture, source_hash, source_version, output, origin, usage_event_id, now):
        with self._write(user_id) as s:
            old = s.scalar(select(ResumeAnalysisReport).where(ResumeAnalysisReport.user_id == user_id,
                                                           ResumeAnalysisReport.operation_hash == operation_hash))
            if old:
                if old.fixture_id != fixture['case_id'] or old.source_hash != source_hash or old.origin != origin:
                    raise AnalysisError("idempotency_conflict")
                return self._view(s, old)
            if s.scalar(select(func.count()).select_from(ResumeAnalysisReport).where(ResumeAnalysisReport.user_id == user_id)) >= MAX_REPORTS_PER_OWNER:
                raise AnalysisError("history_limit")
            if origin == 'provider':
                usage = s.get(AIUsageEvent, usage_event_id)
                if usage is None or usage.user_id != user_id or usage.status != 'succeeded' or usage.fixture_id != fixture['case_id']:
                    raise AnalysisError("invalid_usage_link")
            elif origin != 'reference' or usage_event_id is not None:
                raise AnalysisError("invalid_origin")
            version = 1 + int(s.scalar(select(func.max(ResumeAnalysisReport.version)).where(
                ResumeAnalysisReport.user_id == user_id, ResumeAnalysisReport.fixture_id == fixture['case_id'])) or 0)
            row = ResumeAnalysisReport(id=str(uuid4()), user_id=user_id, operation_hash=operation_hash,
                fixture_id=fixture['case_id'], source_hash=source_hash, source_version=source_version,
                analysis_version=ANALYSIS_VERSION, version=version, language=fixture['language'],
                origin=origin, usage_event_id=usage_event_id, source_json=json.dumps(fixture['source_facts'], ensure_ascii=False),
                result_json=json.dumps(output, ensure_ascii=False, allow_nan=False), created_at=now)
            s.add(row);s.flush()
            for i in range(len(output['recommendations'])):
                s.add(ResumeAnalysisDecision(report_id=row.id, recommendation_id=f'rec-{i+1}', decision='pending', revision=0, updated_at=now))
            s.flush()
            return self._view(s, row)

    def decide(self, *, user_id, report_id, recommendation_id, decision, expected_revision, expected_source_hash, now):
        if decision not in {'accepted','rejected','pending'} or type(expected_revision) is not int or expected_revision < 0:
            raise AnalysisError('invalid_decision')
        with self._write(user_id) as s:
            row = s.scalar(select(ResumeAnalysisReport).where(ResumeAnalysisReport.id == report_id, ResumeAnalysisReport.user_id == user_id))
            if row is None:
                raise AnalysisError('not_found')
            if row.source_hash != expected_source_hash:
                raise AnalysisError('stale_source')
            ds = s.get(ResumeAnalysisDecision, (report_id, recommendation_id))
            if ds is None:
                raise AnalysisError('not_found')
            if ds.revision != expected_revision:
                # A double submitted identical transition is an idempotent no-op.
                if ds.revision == expected_revision + 1 and ds.decision == decision:
                    return self._view(s, row)
                raise AnalysisError('stale_review')
            if ds.decision != decision:
                if s.scalar(select(func.count()).select_from(ResumeAnalysisReviewEvent).where(ResumeAnalysisReviewEvent.report_id==report_id)) >= 500:
                    raise AnalysisError('review_history_limit')
                ds.decision=decision;ds.revision+=1;ds.updated_at=now
                s.add(ResumeAnalysisReviewEvent(id=str(uuid4()), report_id=report_id,
                    recommendation_id=recommendation_id, decision=decision, revision=ds.revision, created_at=now))
                s.flush()
            return self._view(s,row)

    def delete(self, user_id, report_id, source_hash):
        with self._write(user_id) as s:
            row=s.scalar(select(ResumeAnalysisReport).where(ResumeAnalysisReport.id==report_id, ResumeAnalysisReport.user_id==user_id))
            if row is None:raise AnalysisError('not_found')
            if row.source_hash!=source_hash:raise AnalysisError('stale_source')
            s.execute(delete(ResumeAnalysisReport).where(ResumeAnalysisReport.id==report_id, ResumeAnalysisReport.user_id==user_id))
