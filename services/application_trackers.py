"""JOB-002 tracker orchestration; deliberately performs no network or provider I/O."""
import time
from domain.application_tracker import expected_revision_value, state_value


class ApplicationTrackerService:
    def __init__(self, repository):
        self.repository = repository

    def get(self, user_id, saved_id):
        return self.repository.get(user_id, saved_id)

    def transition(self, user_id, saved_id, state, expected_revision, *, now=None):
        return self.repository.transition(user_id, saved_id, state_value(state),
            expected_revision_value(expected_revision), now=int(time.time()) if now is None else now)
