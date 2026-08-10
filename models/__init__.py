"""SQLAlchemy persistence models for the current application schema."""

from .accounts import HeadHunterAccount, SuperJobAccount
from .auth import AuthSession, AuthToken
from .base import Base
from .oauth_connection import OAuthConnection
from .search_snapshot import (
    SearchSnapshot,
    SearchSnapshotCandidate,
    SearchSnapshotItem,
    SearchSnapshotSource,
)
from .sync_checkpoint import SyncCheckpoint
from .sync_run import SyncRun
from .sync_worker import SyncWorker
from .user import User
from .vacancy import Vacancy, VacancySourceRecord

__all__ = [
    "Base",
    "AuthSession",
    "AuthToken",
    "HeadHunterAccount",
    "OAuthConnection",
    "SuperJobAccount",
    "SyncCheckpoint",
    "SyncRun",
    "SyncWorker",
    "SearchSnapshot",
    "SearchSnapshotCandidate",
    "SearchSnapshotItem",
    "SearchSnapshotSource",
    "User",
    "Vacancy",
    "VacancySourceRecord",
]
