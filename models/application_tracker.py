"""JOB-002 current tracker and immutable transition history."""
from sqlalchemy import BigInteger, CheckConstraint, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

_VALID = "'saved','preparing','submitted_user_reported','in_process_user_reported','closed'"


class SavedVacancyTracker(Base):
    __tablename__ = 'saved_vacancy_trackers'
    __table_args__ = (
        ForeignKeyConstraint(['saved_vacancy_id', 'user_id'], ['saved_vacancies.id', 'saved_vacancies.user_id'],
                             ondelete='CASCADE', name='fk_tracker_owned_saved_vacancy'),
        UniqueConstraint('saved_vacancy_id', 'user_id', name='uq_tracker_saved_owner'),
        CheckConstraint(f"state IN ({_VALID})", name='ck_tracker_state'),
        CheckConstraint('revision >= 1', name='ck_tracker_revision'),
        Index('idx_tracker_owner_updated', 'user_id', 'updated_at'),
    )
    saved_vacancy_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class SavedVacancyTrackerEvent(Base):
    __tablename__ = 'saved_vacancy_tracker_events'
    __table_args__ = (
        ForeignKeyConstraint(['saved_vacancy_id', 'user_id'],
                             ['saved_vacancy_trackers.saved_vacancy_id', 'saved_vacancy_trackers.user_id'],
                             ondelete='CASCADE', name='fk_tracker_event_owned_tracker'),
        CheckConstraint(f"from_state IN ({_VALID})", name='ck_tracker_event_from_state'),
        CheckConstraint(f"to_state IN ({_VALID})", name='ck_tracker_event_to_state'),
        CheckConstraint('from_state <> to_state', name='ck_tracker_event_changed'),
        Index('idx_tracker_event_owner_saved_created', 'user_id', 'saved_vacancy_id', 'created_at', 'id'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    saved_vacancy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
