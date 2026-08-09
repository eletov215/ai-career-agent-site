"""SQLAlchemy persistence models for the current application schema."""

from .accounts import HeadHunterAccount, SuperJobAccount
from .base import Base
from .oauth_connection import OAuthConnection
from .sync_checkpoint import SyncCheckpoint
from .sync_run import SyncRun
from .sync_worker import SyncWorker
from .search_snapshot import (
    SearchSnapshot,
    SearchSnapshotCandidate,
    SearchSnapshotItem,
    SearchSnapshotSource,
)
from .user import User
from .vacancy import Vacancy, VacancySourceRecord

__all__ = [
    "Base",
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
