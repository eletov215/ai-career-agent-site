"""Repository layer hiding SQLAlchemy from routes and services."""

from .auth import AuthRepository
from .consent import ConsentConflictError, ConsentOwnerNotFoundError, ConsentRepository
from .oauth_connections import (
    OAuthConnectionOwnershipError,
    OAuthConnectionRepository,
    OAuthProviderAlreadyConnectedError,
)
from .profiles import CareerProfileRepository, CareerProfileVersionConflictError
from .privacy import PrivacyRepository
from .resume_drafts import (
    ResumeDraftConflictError,
    ResumeDraftNotFoundError,
    ResumeDraftRepository,
)
from .search_snapshots import SearchSnapshotRepository
from .source_health import SourceHealthRepository
from .sync_checkpoints import SyncCheckpointRepository
from .sync_runs import SyncRunRepository
from .sync_workers import SyncWorkerRepository
from .users import UserRepository, normalize_email
from .vacancies import VacancyRepository

__all__ = [
    "AuthRepository",
    "ConsentConflictError",
    "ConsentOwnerNotFoundError",
    "ConsentRepository",
    "OAuthConnectionOwnershipError",
    "OAuthConnectionRepository",
    "OAuthProviderAlreadyConnectedError",
    "CareerProfileRepository",
    "CareerProfileVersionConflictError",
    "PrivacyRepository",
    "ResumeDraftConflictError",
    "ResumeDraftNotFoundError",
    "ResumeDraftRepository",
    "SearchSnapshotRepository",
    "SourceHealthRepository",
    "SyncCheckpointRepository",
    "SyncRunRepository",
    "SyncWorkerRepository",
    "UserRepository",
    "VacancyRepository",
    "normalize_email",
]
