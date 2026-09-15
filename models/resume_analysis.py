"""Immutable synthetic analysis reports and separate owner review records."""
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class ResumeAnalysisReport(Base):
    __tablename__ = "resume_analysis_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "operation_hash", name="uq_analysis_owner_operation"),
        UniqueConstraint("user_id", "fixture_id", "version", name="uq_analysis_owner_fixture_version"),
        CheckConstraint("version >= 1", name="ck_analysis_version"),
        CheckConstraint("origin IN ('reference', 'provider')", name="ck_analysis_origin"),
        Index("idx_analysis_owner_created", "user_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fixture_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    operation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Ledger may expire before an explicitly saved report; no cascading FK to it.
    usage_event_id: Mapped[str | None] = mapped_column(String(36))
    source_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

class ResumeAnalysisDecision(Base):
    __tablename__ = "resume_analysis_decisions"
    __table_args__ = (
        CheckConstraint("decision IN ('pending', 'accepted', 'rejected')", name="ck_analysis_decision"),
        CheckConstraint("revision >= 0", name="ck_analysis_decision_revision"),
    )
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_analysis_reports.id", ondelete="CASCADE"), primary_key=True)
    recommendation_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

class ResumeAnalysisReviewEvent(Base):
    __tablename__ = "resume_analysis_review_events"
    __table_args__ = (
        UniqueConstraint("report_id", "recommendation_id", "revision", name="uq_analysis_review_revision"),
        CheckConstraint("decision IN ('pending', 'accepted', 'rejected')", name="ck_analysis_review_decision"),
        CheckConstraint("revision >= 1", name="ck_analysis_review_revision"),
        Index("idx_analysis_review_report", "report_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_analysis_reports.id", ondelete="CASCADE"), nullable=False)
    recommendation_id: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
