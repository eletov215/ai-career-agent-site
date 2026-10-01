"""JOB-002 application tracker state machine (internal, user-reported state only)."""
from __future__ import annotations

import re
from typing import Any

STATES = ('saved', 'preparing', 'submitted_user_reported', 'in_process_user_reported', 'closed')
TRANSITIONS = {
    'saved': frozenset(('preparing', 'submitted_user_reported', 'closed')),
    'preparing': frozenset(('saved', 'submitted_user_reported', 'closed')),
    'submitted_user_reported': frozenset(('preparing', 'in_process_user_reported', 'closed')),
    'in_process_user_reported': frozenset(('submitted_user_reported', 'closed')),
    'closed': frozenset(('saved', 'preparing')),
}


class TrackerError(ValueError):
    """Fixed public error code; caller input and persistence details stay private."""


def state_value(value: Any) -> str:
    if not isinstance(value, str) or value not in STATES:
        raise TrackerError('invalid_state')
    return value


def expected_revision_value(value: Any) -> int:
    if type(value) is int and 0 <= value <= 2147483647:
        return value
    if isinstance(value, str) and re.fullmatch(r'(0|[1-9][0-9]{0,9})', value):
        number = int(value)
        if number <= 2147483647:
            return number
    raise TrackerError('invalid_revision')


def validate_transition(current: str, target: str) -> bool:
    """Return False for a no-op and reject every transition outside the contract."""
    state_value(current)
    state_value(target)
    if current == target:
        return False
    if target not in TRANSITIONS[current]:
        raise TrackerError('invalid_transition')
    return True
