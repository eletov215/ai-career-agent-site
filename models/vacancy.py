"""Canonical vacancies and provider-specific source records."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Vacancy(Base):
    """Canonical vacancy prepared for later cross-source deduplication."""

    __tablename__ = "vacancies"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_vacancies_fingerprint"),
        Index("idx_vacancies_active_updated", "is_active", "updated_at"),
        Index("idx_vacancies_location", "location"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    salary_from: Mapped[float | None] = mapped_column(Float)
    salary_to: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    salary_from: Mapped[float | None] = mapped_column(Float)
    salary_to: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
