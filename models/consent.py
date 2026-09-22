"""Versioned owner-bound consent records for LEGAL-001."""
from __future__ import annotations
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class AIConsent(Base):
    __tablename__ = "ai_consents"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "consent_type", "scope", "policy_version", "policy_hash",
            "provider", "purpose", "cycle", name="uq_ai_consents_policy_cycle"
        ),
        CheckConstraint("cycle >= 1 AND revision >= 1", name="ck_ai_consents_versions"),
        CheckConstraint("status IN ('accepted','withdrawn')", name="ck_ai_consents_status"),
        CheckConstraint(
            "(status = 'accepted' AND withdrawn_at IS NULL) OR "
            "(status = 'withdrawn' AND withdrawn_at IS NOT NULL AND withdrawn_at >= accepted_at)",
            name="ck_ai_consents_withdrawal",
        ),
        Index("idx_ai_consents_owner_created", "user_id", "created_at"),
        Index(
            "idx_ai_consents_owner_policy", "user_id", "consent_type", "scope",
            "policy_version", "provider", "purpose", "cycle",
        ),
        Index(
            "uq_ai_consents_active_policy", "user_id", "consent_type", "scope",
            "policy_version", "policy_hash", "provider", "purpose", unique=True,
            sqlite_where=text("status = 'accepted'"),
            postgresql_where=text("status = 'accepted'"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(96), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(96), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    withdrawn_at: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
