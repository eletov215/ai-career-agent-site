"""JOB-003 in-app-only orchestration. No dispatch or network dependencies."""
import time
from datetime import date
from domain.reminders import due_date_value, enabled_value, revision_value


class ReminderService:
    def __init__(self, repository): self.repository = repository
    def preference(self, user_id): return self.repository.get_preference(user_id)
    def set_preference(self, user_id, enabled, expected_revision, now=None):
        return self.repository.set_preference(user_id, enabled_value(enabled), revision_value(expected_revision), now=int(time.time()) if now is None else now)
    def for_saved(self, user_id, saved_id): return self.repository.get_for_saved(user_id, saved_id)
    def list(self, user_id, today=None):
        today = today or date.today()
        return [row | {'label': 'Просрочено' if due_date_value(row['due_date']) < today else 'Сегодня' if due_date_value(row['due_date']) == today else 'Предстоит'} for row in self.repository.list(user_id)]
    def save(self, user_id, saved_id, due_date, expected_revision, now=None):
        return self.repository.save(user_id, saved_id, due_date_value(due_date), revision_value(expected_revision), now=int(time.time()) if now is None else now)
    def delete(self, user_id, saved_id, expected_revision): return self.repository.delete(user_id, saved_id, revision_value(expected_revision))
