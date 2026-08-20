"""Persistent, PII-free provider health state for SEARCH-005."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SourceHealthState(Base):
    __tablename__ = "source_health_states"
    __table_args__ = (
        CheckConstraint(
            "availability IN ('unknown','available','cached','degraded','auth_required','temporarily_unavailable','disabled')",
            name="ck_source_health_states_availability",
        ),
        CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_source_health_states_failures_nonnegative",
        ),
        CheckConstraint(
            "last_latency_ms IS NULL OR last_latency_ms >= 0",
            name="ck_source_health_states_latency_nonnegative",
        ),
        CheckConstraint(
            "cache_item_count IS NULL OR cache_item_count >= 0",
            name="ck_source_health_states_cache_count_nonnegative",
        ),
        Index("idx_source_health_updated", "updated_at"),
        Index("idx_source_health_availability", "availability"),
    )

    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    availability: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_attempt_at: Mapped[int | None] = mapped_column(BigInteger)
    last_success_at: Mapped[int | None] = mapped_column(BigInteger)
    last_failure_at: Mapped[int | None] = mapped_column(BigInteger)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_category: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(120))
    cache_observed_at: Mapped[int | None] = mapped_column(BigInteger)
    cache_item_count: Mapped[int | None] = mapped_column(Integer)
    details_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
