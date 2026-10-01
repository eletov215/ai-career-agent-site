"""Owner-scoped, atomic JOB-002 tracker persistence."""
from __future__ import annotations
from contextlib import contextmanager
from uuid import uuid4
from sqlalchemy import select, text
from domain.application_tracker import TrackerError, expected_revision_value, state_value, validate_transition
from models import User
from models.saved_vacancy import SavedVacancy
from models.application_tracker import SavedVacancyTracker, SavedVacancyTrackerEvent
from .base import RepositoryBase


def tracker_view(row, events=()):
    if row is None:
        return {'state': 'saved', 'revision': 0, 'created_at': None, 'updated_at': None,
                'events': [event_view(event) for event in events]}
    return {'state': row.state, 'revision': row.revision, 'created_at': row.created_at,
            'updated_at': row.updated_at, 'events': [event_view(event) for event in events]}


def event_view(row):
    return {'id': row.id, 'saved_vacancy_id': row.saved_vacancy_id,
            'from_state': row.from_state, 'to_state': row.to_state, 'created_at': row.created_at}


class ApplicationTrackerRepository(RepositoryBase):
    @contextmanager
    def _write(self, user_id):
        with self.session() as session:
            if self.engine.dialect.name == 'sqlite':
                session.execute(text('BEGIN IMMEDIATE'))
            elif self.engine.dialect.name == 'postgresql':
                session.execute(text("SET LOCAL lock_timeout = '5s'"))
            try:
                owner = session.scalar(select(User).where(User.id == user_id).with_for_update())
                if owner is None or owner.status != 'active' or owner.email_verified_at is None:
                    raise TrackerError('not_found')
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def _saved(session, user_id, saved_id, *, lock=False):
        query = select(SavedVacancy).where(SavedVacancy.user_id == user_id, SavedVacancy.id == saved_id)
        row = session.scalar(query.with_for_update() if lock else query)
        if row is None:
            raise TrackerError('not_found')
        return row

    @staticmethod
    def _tracker(session, user_id, saved_id, *, lock=False):
        query = select(SavedVacancyTracker).where(
            SavedVacancyTracker.user_id == user_id, SavedVacancyTracker.saved_vacancy_id == saved_id)
        return session.scalar(query.with_for_update() if lock else query)

    def get(self, user_id, saved_id):
        with self.session() as session:
            self._saved(session, user_id, saved_id)
            row = self._tracker(session, user_id, saved_id)
            events = session.scalars(select(SavedVacancyTrackerEvent).where(
                SavedVacancyTrackerEvent.user_id == user_id,
                SavedVacancyTrackerEvent.saved_vacancy_id == saved_id
            ).order_by(SavedVacancyTrackerEvent.created_at.desc(), SavedVacancyTrackerEvent.id.desc())).all()
            return tracker_view(row, events)

    def transition(self, user_id, saved_id, target, expected_revision, *, now):
        target, expected_revision = state_value(target), expected_revision_value(expected_revision)
        with self._write(user_id) as session:
            self._saved(session, user_id, saved_id, lock=True)
            row = self._tracker(session, user_id, saved_id, lock=True)
            current, revision = ('saved', 0) if row is None else (row.state, row.revision)
            if revision != expected_revision:
                raise TrackerError('stale_write')
            if not validate_transition(current, target):
                return tracker_view(row)
            if row is None:
                row = SavedVacancyTracker(saved_vacancy_id=saved_id, user_id=user_id, state=target,
                                          revision=1, created_at=now, updated_at=now)
                session.add(row)
            else:
                row.state, row.revision, row.updated_at = target, row.revision + 1, now
            session.add(SavedVacancyTrackerEvent(id=str(uuid4()), saved_vacancy_id=saved_id,
                        user_id=user_id, from_state=current, to_state=target, created_at=now))
            session.flush()
            return tracker_view(row)
