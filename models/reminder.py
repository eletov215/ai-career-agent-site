"""JOB-003 owner preferences and calendar-date reminders."""
from datetime import date
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class NotificationPreference(Base):
    __tablename__ = 'notification_preferences'
    __table_args__ = (CheckConstraint('revision >= 1', name='ck_notification_preference_revision'),)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    in_app_reminders_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class SavedVacancyReminder(Base):
    __tablename__ = 'saved_vacancy_reminders'
    __table_args__ = (
        ForeignKeyConstraint(['saved_vacancy_id', 'user_id'], ['saved_vacancies.id', 'saved_vacancies.user_id'], ondelete='CASCADE', name='fk_reminder_owned_saved_vacancy'),
        UniqueConstraint('user_id', 'saved_vacancy_id', name='uq_reminder_owner_saved'),
        CheckConstraint('revision >= 1', name='ck_saved_vacancy_reminder_revision'),
        Index('idx_reminder_owner_due_date', 'user_id', 'due_date'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    saved_vacancy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
