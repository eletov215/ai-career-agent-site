"""Unified external OAuth connection model."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class OAuthConnection(Base):
    """Encrypted connection to one external job platform identity."""

    __tablename__ = "oauth_connections"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "external_user_id",
            name="uq_oauth_connections_provider_external_user",
        ),
        Index("idx_oauth_connections_user", "user_id"),
        Index("idx_oauth_connections_provider", "provider"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[int | None] = mapped_column(BigInteger)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    user = relationship("User", back_populates="oauth_connections")
