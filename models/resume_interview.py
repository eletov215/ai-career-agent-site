"""AI-003 reference sessions and append-only transition events."""
from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ResumeInterviewSession(Base):
    __tablename__ = 'resume_interview_sessions'
    __table_args__ = (
        UniqueConstraint('user_id', 'operation_hash', name='uq_interview_owner_operation'),
        UniqueConstraint('draft_id', name='uq_interview_draft'),
        CheckConstraint("origin = 'reference'", name='ck_interview_origin'),
        CheckConstraint("status IN ('active', 'review', 'confirmed')", name='ck_interview_status'),
        CheckConstraint("language IN ('ru', 'en')", name='ck_interview_language'),
        CheckConstraint('revision >= 1 AND revision <= 60', name='ck_interview_revision'),
        CheckConstraint('draft_revision >= 1', name='ck_interview_draft_revision'),
        Index('idx_interview_owner_updated', 'user_id', 'updated_at'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    draft_id: Mapped[str] = mapped_column(String(36), ForeignKey('resume_drafts.id', ondelete='CASCADE'), nullable=False)
    fixture_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_json: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    operation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed_text: Mapped[str | None] = mapped_column(Text)
    confirmed_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('resume_versions.id', ondelete='SET NULL'))
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ResumeInterviewEvent(Base):
    __tablename__ = 'resume_interview_events'
    __table_args__ = (
        UniqueConstraint('session_id', 'revision', name='uq_interview_event_revision'),
        UniqueConstraint('session_id', 'operation_hash', name='uq_interview_event_operation'),
        CheckConstraint("kind IN ('started', 'answered', 'skipped', 'rewound', 'confirmed')", name='ck_interview_event_kind'),
        CheckConstraint('revision >= 1 AND revision <= 60', name='ck_interview_event_revision'),
        Index('idx_interview_event_session', 'session_id', 'revision'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey('resume_interview_sessions.id', ondelete='CASCADE'), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
