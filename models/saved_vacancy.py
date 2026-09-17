"""Persistent owner snapshots intentionally have no foreign key to search/cache."""
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class SavedVacancy(Base):
    __tablename__ = 'saved_vacancies'
    __table_args__ = (
        UniqueConstraint('id', 'user_id', name='uq_saved_vacancy_id_owner'),
        CheckConstraint('revision >= 1', name='ck_saved_vacancy_revision'),
        Index('idx_saved_vacancy_owner_created', 'user_id', 'created_at', 'id'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_version: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default='')
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class SavedVacancySource(Base):
    __tablename__ = 'saved_vacancy_sources'
    __table_args__ = (
        ForeignKeyConstraint(['saved_vacancy_id', 'user_id'], ['saved_vacancies.id', 'saved_vacancies.user_id'],
                             ondelete='CASCADE', name='fk_saved_source_owned_snapshot'),
        UniqueConstraint('user_id', 'identity_hash', name='uq_saved_source_owner_identity'),
        Index('idx_saved_source_snapshot', 'saved_vacancy_id', 'user_id'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    saved_vacancy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
