"""First-party authentication persistence models for AUTH-001."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AuthSession(Base):
    """Revocable browser session backed by an opaque client token hash."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
        Index(
            "idx_auth_sessions_user_active",
            "user_id",
            "revoked_at",
            "expires_at",
        ),
        Index("idx_auth_sessions_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_seen_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    revoked_at: Mapped[int | None] = mapped_column(BigInteger)
    revoke_reason: Mapped[str | None] = mapped_column(String(64))
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))

    user = relationship("User", back_populates="auth_sessions")


class AuthToken(Base):
    """Single-use, expiring verification or password-reset token."""

    __tablename__ = "auth_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_auth_tokens_token_hash"),
        Index("idx_auth_tokens_user_purpose", "user_id", "purpose"),
        Index("idx_auth_tokens_expires", "expires_at"),
        Index("idx_auth_tokens_consumed", "consumed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    consumed_at: Mapped[int | None] = mapped_column(BigInteger)
    consumed_reason: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", back_populates="auth_tokens")
