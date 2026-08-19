"""Privacy control audit persistence for PRIV-001."""

from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PrivacyAuditEvent(Base):
    """Identifier-free audit event for privacy control operations.

    The row deliberately contains no user ID, email, token, filename, resume
    content, or provider identity. It records only event type, bounded aggregate
    counts and timestamp so an account deletion can be audited without retaining
    the deleted person's data.
    """

    __tablename__ = "privacy_audit_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('data_exported', 'account_deleted', 'retention_cleanup')",
            name="ck_privacy_audit_events_type",
        ),
        Index("idx_privacy_audit_events_created", "created_at"),
        Index("idx_privacy_audit_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    counts_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
