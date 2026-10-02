"""Pure validation rules for JOB-003 calendar-date reminders."""
from datetime import date


class ReminderError(ValueError):
    pass


def revision_value(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ReminderError('invalid_revision') from None
    if value < 0:
        raise ReminderError('invalid_revision')
    return value


def due_date_value(raw):
    try:
        value = date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        raise ReminderError('invalid_date') from None
    if value.isoformat() != str(raw):
        raise ReminderError('invalid_date')
    return value


def enabled_value(raw):
    if raw == '1' or raw is True:
        return True
    if raw == '0' or raw is False:
        return False
    raise ReminderError('invalid_preference')
