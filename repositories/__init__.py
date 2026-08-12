"""Repository layer hiding SQLAlchemy from routes and services."""

from .auth import AuthRepository
from .oauth_connections import (
    OAuthConnectionOwnershipError,
    OAuthConnectionRepository,
    OAuthProviderAlreadyConnectedError,
)
from .profiles import CareerProfileRepository, CareerProfileVersionConflictError
from .search_snapshots import SearchSnapshotRepository
from .sync_checkpoints import SyncCheckpointRepository
from .sync_runs import SyncRunRepository
from .sync_workers import SyncWorkerRepository
from .users import UserRepository, normalize_email
from .vacancies import VacancyRepository

__all__ = [
    "AuthRepository",
    "OAuthConnectionOwnershipError",
    "OAuthConnectionRepository",
    "OAuthProviderAlreadyConnectedError",
    "CareerProfileRepository",
    "CareerProfileVersionConflictError",
    "SearchSnapshotRepository",
    "SyncCheckpointRepository",
    "SyncRunRepository",
    "SyncWorkerRepository",
    "UserRepository",
    "VacancyRepository",
    "normalize_email",
]
