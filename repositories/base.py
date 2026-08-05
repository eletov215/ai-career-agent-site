"""Shared repository plumbing."""

from __future__ import annotations

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from database import DatabaseRuntime


class RepositoryBase:
    """Provide short-lived SQLAlchemy sessions to concrete repositories."""

    def __init__(self, database: DatabaseRuntime | Engine):
        if isinstance(database, DatabaseRuntime):
            self.engine = database.engine
            self._sessions = database.session_factory
        else:
            self.engine = database
            self._sessions = sessionmaker(
                bind=database,
                autoflush=False,
                expire_on_commit=False,
                future=True,
            )

    def session(self) -> Session:
        return self._sessions()
