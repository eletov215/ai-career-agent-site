"""Application user model prepared for the first-party account system."""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    """First-party AI Career Agent identity.

    DATA-002 introduces the table and repository only.  Passwords, verification
    tokens, and account UI are intentionally deferred to AUTH-001.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
        Index("idx_users_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str | None] = mapped_column(Text)
    normalized_email: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    email_verified_at: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    oauth_connections = relationship(
        "OAuthConnection",
        back_populates="user",
        passive_deletes=True,
    )
