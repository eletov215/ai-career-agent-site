"""Repository for first-party users."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import select

from domain import UserRecord
from models import User

from .base import RepositoryBase


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


class UserRepository(RepositoryBase):
    """Create and retrieve application users without leaking ORM objects."""

    @staticmethod
    def _record(row: User) -> UserRecord:
        return UserRecord(
            id=row.id,
            email=row.email,
            normalized_email=row.normalized_email,
            display_name=row.display_name,
            status=row.status,
            email_verified_at=row.email_verified_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create(
        self,
        *,
        email: str | None = None,
        display_name: str | None = None,
        status: str = "pending",
        user_id: str | None = None,
    ) -> UserRecord:
        now = int(time.time())
        row = User(
            id=user_id or str(uuid.uuid4()),
            email=email.strip() if email and email.strip() else None,
            normalized_email=normalize_email(email),
            display_name=display_name.strip() if display_name and display_name.strip() else None,
            status=status,
            email_verified_at=None,
            created_at=now,
            updated_at=now,
        )
        with self.session() as session:
            session.add(row)
            session.commit()
            return self._record(row)

    def get(self, user_id: str) -> UserRecord | None:
        with self.session() as session:
            row = session.get(User, user_id)
            return self._record(row) if row else None

    def find_by_email(self, email: str) -> UserRecord | None:
        normalized = normalize_email(email)
        if not normalized:
            return None
        with self.session() as session:
            row = session.scalar(
                select(User).where(User.normalized_email == normalized)
            )
            return self._record(row) if row else None
