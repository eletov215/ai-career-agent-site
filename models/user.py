"""First-party AI Career Agent user identity."""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    """First-party identity used by AUTH-001 and later profile packages."""

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
    password_hash: Mapped[str | None] = mapped_column(Text)
    password_changed_at: Mapped[int | None] = mapped_column(BigInteger)
    last_login_at: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    oauth_connections = relationship(
        "OAuthConnection",
        back_populates="user",
        passive_deletes=True,
    )
    auth_sessions = relationship(
        "AuthSession",
        back_populates="user",
        passive_deletes=True,
    )
    auth_tokens = relationship(
        "AuthToken",
        back_populates="user",
        passive_deletes=True,
    )
    career_profile = relationship(
        "CareerProfile",
        back_populates="user",
        passive_deletes=True,
        uselist=False,
    )
    resume_drafts = relationship(
        "ResumeDraft",
        back_populates="user",
        passive_deletes=True,
    )
