"""AI004-M04B: separate durable user-owned matching reports and cache claims.

Historical synthetic/reference-only vacancy_match_* records are untouched.
These tables are NOT wired to HTTP routes, providers or legal admission.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger, CheckConstraint, ForeignKey, ForeignKeyConstraint,
    Index, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserMatchReport(Base):
    __tablename__ = "user_match_reports"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_user_match_report_id_owner"),
        UniqueConstraint("user_id", "cache_key_hash", name="uq_user_match_report_owner_key"),
        UniqueConstraint("user_id", "usage_event_id", name="uq_user_match_report_owner_usage"),
        ForeignKeyConstraint(
            ["saved_vacancy_id", "user_id"],
            ["saved_vacancies.id", "saved_vacancies.user_id"],
            ondelete="CASCADE", name="fk_user_match_report_owned_vacancy",
        ),
        CheckConstraint(
            "source_kind IN ('saved','search')", name="ck_user_match_report_source_kind",
        ),
        CheckConstraint(
            "(source_kind = 'saved' AND saved_vacancy_id IS NOT NULL) OR "
            "(source_kind = 'search' AND saved_vacancy_id IS NULL)",
            name="ck_user_match_report_source_link",
        ),
        Index("idx_user_match_report_owner_created", "user_id", "created_at", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    resume_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    saved_vacancy_id: Mapped[str | None] = mapped_column(String(36))
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    vacancy_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cache_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resume_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vacancy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    classification_version: Mapped[str] = mapped_column(String(64), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    usage_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # Signed, canonical, M03-validated snippets. No contacts/messages/raw provider data.
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_seal: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class UserMatchCache(Base):
    __tablename__ = "user_match_cache"
    __table_args__ = (
        UniqueConstraint("user_id", "cache_key_hash", name="uq_user_match_cache_owner_key"),
        ForeignKeyConstraint(
            ["saved_vacancy_id", "user_id"],
            ["saved_vacancies.id", "saved_vacancies.user_id"],
            ondelete="CASCADE", name="fk_user_match_cache_owned_vacancy",
        ),
        ForeignKeyConstraint(
            ["report_id", "user_id"], ["user_match_reports.id", "user_match_reports.user_id"],
            ondelete="CASCADE", name="fk_user_match_cache_owned_report",
        ),
        CheckConstraint(
            "state IN ('pending','ready','failed','unknown')",
            name="ck_user_match_cache_state",
        ),
        CheckConstraint(
            "(state = 'ready' AND report_id IS NOT NULL) OR "
            "(state <> 'ready' AND report_id IS NULL)",
            name="ck_user_match_cache_ready_report",
        ),
        CheckConstraint(
            "(source_kind = 'saved' AND saved_vacancy_id IS NOT NULL) OR "
            "(source_kind = 'search' AND saved_vacancy_id IS NULL)",
            name="ck_user_match_cache_source_link",
        ),
        CheckConstraint(
            "lease_expires_at >= 0", name="ck_user_match_cache_lease",
        ),
        Index("idx_user_match_cache_owner_updated", "user_id", "updated_at", "id"),
        Index("idx_user_match_cache_state_lease", "state", "lease_expires_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    resume_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    saved_vacancy_id: Mapped[str | None] = mapped_column(String(36))
    source_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    vacancy_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    cache_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    report_id: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
