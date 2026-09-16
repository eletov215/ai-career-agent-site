"""Owner-scoped AI-003 persistence. All writes are short, network-free transactions."""
from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Callable
import json
from uuid import uuid4

from sqlalchemy import func, select, text
from models import ResumeDraft, ResumeVersion, User
from models.resume_interview import ResumeInterviewEvent, ResumeInterviewSession
from domain.resume_interview import InterviewError, MAX_EVENTS_PER_SESSION, MAX_SESSIONS_PER_OWNER
from .base import RepositoryBase


def interview_snapshot(row, events=()) -> dict:
    """Privacy-safe stored view; excludes operation and request fingerprints."""
    return {
        'id': row.id, 'draft_id': row.draft_id, 'fixture_id': row.fixture_id,
        'source_hash': row.source_hash, 'contract_version': row.contract_version,
        'source': json.loads(row.source_json), 'language': row.language, 'origin': row.origin,
        'revision': row.revision, 'status': row.status, 'answers': json.loads(row.answers_json),
        'draft_revision': row.draft_revision, 'draft_content_hash': row.draft_content_hash,
        'confirmed_text': row.confirmed_text, 'confirmed_version_id': row.confirmed_version_id,
        'created_at': row.created_at, 'updated_at': row.updated_at,
        'events': [{'revision': e.revision, 'kind': e.kind, 'payload': json.loads(e.payload_json),
                    'created_at': e.created_at} for e in events],
    }


class ResumeInterviewRepository(RepositoryBase):
    @contextmanager
    def _write(self, user_id: str):
        with self.session() as session:
            # SQLite does not implement SELECT FOR UPDATE. IMMEDIATE makes the
            # read-check-write sequence atomic there too (including concurrent tests).
            if self.engine.dialect.name == 'sqlite':
                session.execute(text('BEGIN IMMEDIATE'))
            owner = session.scalar(select(User).where(User.id == user_id).with_for_update())
            if owner is None or owner.status != 'active' or owner.email_verified_at is None:
                raise InterviewError('verified_account_required')
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def _owned(user_id: str):
        # Fail closed for a corrupted owner/draft relationship as well as IDOR.
        return select(ResumeInterviewSession).join(
            ResumeDraft, ResumeDraft.id == ResumeInterviewSession.draft_id
        ).where(ResumeInterviewSession.user_id == user_id, ResumeDraft.user_id == user_id)

    @staticmethod
    def _view(session, row) -> dict:
        events = session.scalars(select(ResumeInterviewEvent).where(
            ResumeInterviewEvent.session_id == row.id
        ).order_by(ResumeInterviewEvent.revision)).all()
        return interview_snapshot(row, events)

    def get(self, user_id: str, session_id: str) -> dict | None:
        with self.session() as session:
            row = session.scalar(self._owned(user_id).where(ResumeInterviewSession.id == session_id))
            return self._view(session, row) if row else None

    def for_draft(self, user_id: str, draft_id: str) -> str | None:
        with self.session() as session:
            row = session.scalar(self._owned(user_id).where(ResumeInterviewSession.draft_id == draft_id))
            return row.id if row else None

    def list(self, user_id: str) -> list[dict]:
        with self.session() as session:
            rows = session.scalars(self._owned(user_id).order_by(
                ResumeInterviewSession.updated_at.desc(), ResumeInterviewSession.id.desc()
            ).limit(MAX_SESSIONS_PER_OWNER)).all()
            return [{'id': r.id, 'draft_id': r.draft_id, 'fixture_id': r.fixture_id,
                     'language': r.language, 'status': r.status, 'revision': r.revision,
                     'created_at': r.created_at, 'updated_at': r.updated_at} for r in rows]

    def start(self, *, user_id: str, operation_hash: str, source: dict, source_hash: str,
              seed: dict, now: int) -> dict:
        with self._write(user_id) as session:
            old = session.scalar(self._owned(user_id).where(ResumeInterviewSession.operation_hash == operation_hash))
            if old:
                if old.fixture_id != source['fixture_id'] or old.source_hash != source_hash:
                    raise InterviewError('idempotency_conflict')
                return self._view(session, old)
            count = session.scalar(select(func.count()).select_from(ResumeInterviewSession).where(
                ResumeInterviewSession.user_id == user_id)) or 0
            if count >= MAX_SESSIONS_PER_OWNER:
                raise InterviewError('history_limit')
            # No caller-supplied draft ID: reference work can never attach itself to
            # or overwrite a real user's existing resume.
            draft = ResumeDraft(id=str(uuid4()), user_id=user_id, schema_version=1, revision=1,
                                title=source['title'], state_json=seed['state_json'],
                                content_hash=seed['content_hash'], completion_percent=seed['completion_percent'],
                                profile_version=None, created_at=now, updated_at=now)
            session.add(draft)
            session.flush()
            row = ResumeInterviewSession(id=str(uuid4()), user_id=user_id, draft_id=draft.id,
                fixture_id=source['fixture_id'], source_hash=source_hash, contract_version=source['contract_version'],
                source_json=json.dumps(source, ensure_ascii=False), language=source['language'], origin='reference',
                operation_hash=operation_hash, revision=1, status='active', answers_json='[]',
                draft_revision=draft.revision, draft_content_hash=draft.content_hash,
                confirmed_text=None, confirmed_version_id=None, created_at=now, updated_at=now)
            session.add(row)
            session.flush()
            session.add(ResumeInterviewEvent(id=str(uuid4()), session_id=row.id, revision=1,
                operation_hash=operation_hash, request_hash=source_hash, kind='started', payload_json='{}', created_at=now))
            session.flush()
            return self._view(session, row)

    def transition(self, *, user_id: str, session_id: str, operation_hash: str, request_hash: str,
                   expected_revision: int, source_hash: str, change: Callable, now: int) -> dict:
        with self._write(user_id) as session:
            row = session.scalar(self._owned(user_id).where(ResumeInterviewSession.id == session_id))
            if row is None:
                raise InterviewError('not_found')
            # Match locking order used by existing draft operations. Owner locking
            # serializes interview writes; the draft lock also excludes autosave.
            draft = session.scalar(select(ResumeDraft).where(ResumeDraft.id == row.draft_id,
                ResumeDraft.user_id == user_id).with_for_update())
            if draft is None:
                raise InterviewError('not_found')
            prior = session.scalar(select(ResumeInterviewEvent).where(
                ResumeInterviewEvent.session_id == row.id, ResumeInterviewEvent.operation_hash == operation_hash))
            if prior:
                if prior.request_hash != request_hash:
                    raise InterviewError('idempotency_conflict')
                return self._view(session, row)
            if row.source_hash != source_hash:
                raise InterviewError('stale_source')
            if row.revision != expected_revision:
                raise InterviewError('stale_interview')
            if row.revision >= MAX_EVENTS_PER_SESSION:
                raise InterviewError('history_limit')
            if row.status == 'confirmed':
                raise InterviewError('already_confirmed')
            update = change(interview_snapshot(row), json.loads(draft.state_json))
            draft_change = update.get('draft_change')
            if draft_change is not None:
                if draft.revision != row.draft_revision or draft.content_hash != row.draft_content_hash:
                    raise InterviewError('stale_draft')
                draft.revision += 1
                draft.state_json = draft_change['state_json']
                draft.content_hash = draft_change['content_hash']
                draft.completion_percent = draft_change['completion_percent']
                draft.updated_at = now
                number = 1 + int(session.scalar(select(func.max(ResumeVersion.version)).where(
                    ResumeVersion.draft_id == draft.id)) or 0)
                version = ResumeVersion(id=str(uuid4()), draft_id=draft.id, schema_version=draft.schema_version,
                    version=number, draft_revision=draft.revision, snapshot_json=draft.state_json,
                    content_hash=draft.content_hash, reason='checkpoint', restored_from_version=None, created_at=now)
                session.add(version)
                session.flush()
                row.confirmed_version_id = version.id
                row.confirmed_text = update['confirmed_text']
            row.answers_json = json.dumps(update['answers'], ensure_ascii=False)
            row.status = update['status']
            row.revision += 1
            row.updated_at = now
            session.add(ResumeInterviewEvent(id=str(uuid4()), session_id=row.id, revision=row.revision,
                operation_hash=operation_hash, request_hash=request_hash, kind=update['kind'],
                payload_json=json.dumps(update['event'], ensure_ascii=False), created_at=now))
            session.flush()
            return self._view(session, row)
