"""Domain-facing records detached from SQLAlchemy sessions."""

from .entities import (
    OAuthConnectionRecord,
    SourceRecord,
    SyncCheckpointRecord,
    SyncRunRecord,
    SyncWorkerRecord,
    UserRecord,
    VacancyRecord,
)

__all__ = [
    "OAuthConnectionRecord",
    "SourceRecord",
    "SyncCheckpointRecord",
    "SyncRunRecord",
    "SyncWorkerRecord",
    "UserRecord",
    "VacancyRecord",
]
