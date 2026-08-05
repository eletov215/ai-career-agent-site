"""Domain-facing records detached from SQLAlchemy sessions."""

from .entities import (
    OAuthConnectionRecord,
    SourceRecord,
    SyncRunRecord,
    UserRecord,
    VacancyRecord,
)

__all__ = [
    "OAuthConnectionRecord",
    "SourceRecord",
    "SyncRunRecord",
    "UserRecord",
    "VacancyRecord",
]
