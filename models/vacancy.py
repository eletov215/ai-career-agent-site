"""Persistence model for normalized vacancy cache entries."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Float, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Vacancy(Base):
    """A source vacancy cached in the common application database."""

    __tablename__ = "vacancies"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_vacancies_source_external_id",
        ),
        Index("idx_vacancies_source_fetched", "source", "fetched_at"),
        Index("idx_vacancies_remote", "remote"),
        Index("idx_vacancies_location", "location"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    fetched_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
