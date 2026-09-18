"""Owned cover-letter workspace, immutable reviewed versions and proposals."""
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class CoverLetter(Base):
    __tablename__ = 'cover_letters'
    __table_args__ = (
        UniqueConstraint('id', 'user_id', name='uq_letter_id_owner'),
        UniqueConstraint('user_id', 'operation_hash', name='uq_letter_owner_operation'),
        ForeignKeyConstraint(['saved_vacancy_id', 'user_id'], ['saved_vacancies.id', 'saved_vacancies.user_id'],
                             ondelete='CASCADE', name='fk_letter_owned_vacancy'),
        CheckConstraint('revision >= 1 AND last_version >= 0', name='ck_letter_revisions'),
        Index('idx_letter_owner_vacancy', 'user_id', 'saved_vacancy_id', 'created_at'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    saved_vacancy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    last_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

class CoverLetterVersion(Base):
    __tablename__ = 'cover_letter_versions'
    __table_args__ = (
        ForeignKeyConstraint(['letter_id', 'user_id'], ['cover_letters.id', 'cover_letters.user_id'],
                             ondelete='CASCADE', name='fk_letter_version_owner'),
        UniqueConstraint('letter_id', 'number', name='uq_letter_version_number'),
        CheckConstraint('number >= 1', name='ck_letter_version_number'),
        Index('idx_letter_version_owner', 'user_id', 'letter_id'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    letter_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

class CoverLetterProposal(Base):
    __tablename__ = 'cover_letter_proposals'
    __table_args__ = (
        ForeignKeyConstraint(['letter_id', 'user_id'], ['cover_letters.id', 'cover_letters.user_id'],
                             ondelete='CASCADE', name='fk_letter_proposal_owner'),
        UniqueConstraint('user_id', 'operation_hash', name='uq_letter_proposal_operation'),
        CheckConstraint("status IN ('pending','accepted','rejected')", name='ck_letter_proposal_status'),
        CheckConstraint('base_revision >= 1', name='ck_letter_proposal_revision'),
        Index('idx_letter_proposal_owner', 'user_id', 'letter_id'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    letter_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    base_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
