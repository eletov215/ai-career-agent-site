"""Immutable owner-bound match snapshots and durable version counters."""
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class VacancyMatchSeries(Base):
    __tablename__ = "vacancy_match_series"
    __table_args__ = (CheckConstraint("last_version >= 0", name="ck_match_series_version"),)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    fixture_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_version: Mapped[int] = mapped_column(Integer, nullable=False)

class VacancyMatchReport(Base):
    __tablename__ = "vacancy_match_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "operation_hash", name="uq_match_owner_operation"),
        UniqueConstraint("user_id", "fixture_id", "version", name="uq_match_owner_fixture_version"),
        CheckConstraint("version >= 1", name="ck_match_report_version"),
        CheckConstraint("origin IN ('reference', 'provider')", name="ck_match_report_origin"),
        CheckConstraint("language IN ('ru', 'en')", name="ck_match_report_language"),
        Index("idx_match_owner_created", "user_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fixture_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    operation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vacancy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    # No cascading link to the shorter-lived accounting ledger.
    usage_event_id: Mapped[str | None] = mapped_column(String(36))
    source_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
