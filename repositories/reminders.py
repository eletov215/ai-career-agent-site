"""Owner-scoped atomic persistence for JOB-003."""
from contextlib import contextmanager
from uuid import uuid4
from sqlalchemy import select, text
from domain.reminders import ReminderError
from models import User
from models.saved_vacancy import SavedVacancy
from models.reminder import NotificationPreference, SavedVacancyReminder
from .base import RepositoryBase


def preference_view(row):
    return {'in_app_reminders_enabled': False, 'revision': 0} if row is None else {
        'in_app_reminders_enabled': row.in_app_reminders_enabled, 'revision': row.revision,
        'created_at': row.created_at, 'updated_at': row.updated_at}


def reminder_view(row):
    return {'id': row.id, 'saved_vacancy_id': row.saved_vacancy_id,
            'due_date': row.due_date.isoformat(), 'revision': row.revision,
            'created_at': row.created_at, 'updated_at': row.updated_at}


class ReminderRepository(RepositoryBase):
    @contextmanager
    def _write(self, user_id):
        with self.session() as session:
            if self.engine.dialect.name == 'sqlite': session.execute(text('BEGIN IMMEDIATE'))
            elif self.engine.dialect.name == 'postgresql': session.execute(text("SET LOCAL lock_timeout = '5s'"))
            try:
                owner = session.scalar(select(User).where(User.id == user_id).with_for_update())
                if owner is None or owner.status != 'active' or owner.email_verified_at is None: raise ReminderError('not_found')
                yield session
                session.commit()
            except Exception:
                session.rollback(); raise

    def get_preference(self, user_id):
        with self.session() as session:
            return preference_view(session.get(NotificationPreference, user_id))

    def set_preference(self, user_id, enabled, expected_revision, *, now):
        with self._write(user_id) as session:
            row = session.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user_id).with_for_update())
            revision = row.revision if row else 0
            if revision != expected_revision: raise ReminderError('stale_write')
            if row and row.in_app_reminders_enabled == enabled: return preference_view(row)
            if row is None:
                row = NotificationPreference(user_id=user_id, in_app_reminders_enabled=enabled, revision=1, created_at=now, updated_at=now); session.add(row)
            else:
                row.in_app_reminders_enabled = enabled; row.revision += 1; row.updated_at = now
            session.flush(); return preference_view(row)

    @staticmethod
    def _saved(session, user_id, saved_id, lock=False):
        q = select(SavedVacancy).where(SavedVacancy.user_id == user_id, SavedVacancy.id == saved_id)
        row = session.scalar(q.with_for_update() if lock else q)
        if row is None: raise ReminderError('not_found')
        return row

    def get_for_saved(self, user_id, saved_id):
        with self.session() as session:
            self._saved(session, user_id, saved_id)
            row = session.scalar(select(SavedVacancyReminder).where(SavedVacancyReminder.user_id == user_id, SavedVacancyReminder.saved_vacancy_id == saved_id))
            return reminder_view(row) if row else None

    def list(self, user_id):
        with self.session() as session:
            preference = session.get(NotificationPreference, user_id)
            if preference is None or not preference.in_app_reminders_enabled:
                return []
            rows = session.scalars(select(SavedVacancyReminder).where(SavedVacancyReminder.user_id == user_id).order_by(SavedVacancyReminder.due_date, SavedVacancyReminder.id)).all()
            return [reminder_view(row) for row in rows]

    def save(self, user_id, saved_id, due_date, expected_revision, *, now):
        with self._write(user_id) as session:
            preference = session.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user_id).with_for_update())
            if preference is None or not preference.in_app_reminders_enabled:
                raise ReminderError('preference_disabled')
            self._saved(session, user_id, saved_id, True)
            row = session.scalar(select(SavedVacancyReminder).where(SavedVacancyReminder.user_id == user_id, SavedVacancyReminder.saved_vacancy_id == saved_id).with_for_update())
            revision = row.revision if row else 0
            if revision != expected_revision: raise ReminderError('stale_write')
            if row and row.due_date == due_date: return reminder_view(row)
            if row is None:
                row = SavedVacancyReminder(id=str(uuid4()), user_id=user_id, saved_vacancy_id=saved_id, due_date=due_date, revision=1, created_at=now, updated_at=now); session.add(row)
            else:
                row.due_date = due_date; row.revision += 1; row.updated_at = now
            session.flush(); return reminder_view(row)

    def delete(self, user_id, saved_id, expected_revision):
        with self._write(user_id) as session:
            self._saved(session, user_id, saved_id, True)
            row = session.scalar(select(SavedVacancyReminder).where(SavedVacancyReminder.user_id == user_id, SavedVacancyReminder.saved_vacancy_id == saved_id).with_for_update())
            if row is None: raise ReminderError('not_found')
            if row.revision != expected_revision: raise ReminderError('stale_write')
            session.delete(row)
