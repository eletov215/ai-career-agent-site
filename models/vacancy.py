"""Canonical vacancies and provider-specific source records."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Vacancy(Base):
    """Canonical vacancy that can aggregate proven source publications."""

    __tablename__ = "vacancies"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_vacancies_fingerprint"),
        Index("idx_vacancies_active_updated", "is_active", "updated_at"),
        Index("idx_vacancies_location", "location"),
        Index("idx_vacancies_dedup_key", "dedup_key"),
        Index("idx_vacancies_work_format", "work_format"),
        Index("idx_vacancies_employment_code", "employment_code"),
        Index("idx_vacancies_experience_code", "experience_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str | None] = mapped_column(Text)
    dedup_key: Mapped[str | None] = mapped_column(String(64))
    dedup_version: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    salary_from: Mapped[float | None] = mapped_column(Float)
    salary_to: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    work_format: Mapped[str | None] = mapped_column(String(32))
    employment_code: Mapped[str | None] = mapped_column(String(32))
    experience_code: Mapped[str | None] = mapped_column(String(32))
    schedule: Mapped[str | None] = mapped_column(Text)
    employment: Mapped[str | None] = mapped_column(Text)
    experience: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source_records = relationship(
        "VacancySourceRecord",
        back_populates="vacancy",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class VacancySourceRecord(Base):
    """Provider-specific vacancy payload linked to a canonical vacancy."""

    __tablename__ = "vacancy_source_records"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_vacancy_source_records_source_external_id",
        ),
        Index("idx_vacancy_source_records_vacancy", "vacancy_id"),
        Index("idx_vacancy_source_records_source_fetched", "source", "fetched_at"),
        Index("idx_vacancy_source_records_remote", "remote"),
        Index("idx_vacancy_source_records_location", "location"),
        Index("idx_vacancy_source_records_dedup_key", "dedup_key"),
        Index(
            "idx_vacancy_source_records_source_work_format",
            "source",
            "work_format",
        ),
        Index(
            "idx_vacancy_source_records_source_employment_code",
            "source",
            "employment_code",
        ),
        Index(
            "idx_vacancy_source_records_source_experience_code",
            "source",
            "experience_code",
        ),
        Index(
            "idx_vacancy_source_records_source_status_published",
            "source",
            "source_status",
            "published_at",
        ),
        Index("idx_vacancy_source_records_closed_at", "closed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[str | None] = mapped_column(String(64))
    dedup_version: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    salary_from: Mapped[float | None] = mapped_column(Float)
    salary_to: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    work_format: Mapped[str | None] = mapped_column(String(32))
    employment_code: Mapped[str | None] = mapped_column(String(32))
    experience_code: Mapped[str | None] = mapped_column(String(32))
    schedule: Mapped[str | None] = mapped_column(Text)
    employment: Mapped[str | None] = mapped_column(Text)
    experience: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    search_text: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[str | None] = mapped_column(Text)
    source_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    source_modified_at: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[int | None] = mapped_column(BigInteger)
    closed_reason: Mapped[str | None] = mapped_column(String(64))
    last_seen_run_id: Mapped[str | None] = mapped_column(String(36))
    first_seen_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_seen_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fetched_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    vacancy = relationship("Vacancy", back_populates="source_records")
