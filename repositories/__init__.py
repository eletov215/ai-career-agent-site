"""Repository layer hiding SQLAlchemy from routes and services."""

from .oauth_connections import OAuthConnectionRepository
from .sync_runs import SyncRunRepository
from .sync_workers import SyncWorkerRepository
from .users import UserRepository, normalize_email
from .vacancies import VacancyRepository

__all__ = [
    "OAuthConnectionRepository",
    "SyncRunRepository",
    "SyncWorkerRepository",
    "UserRepository",
    "VacancyRepository",
    "normalize_email",
]
