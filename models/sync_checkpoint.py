"""Persistent incremental synchronization checkpoint state."""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SyncCheckpoint(Base):
    """Durable watermark, continuation cursor, and retry state per source."""

    __tablename__ = "sync_checkpoints"

    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    watermark_at: Mapped[int | None] = mapped_column(BigInteger)
    pending_from_at: Mapped[int | None] = mapped_column(BigInteger)
    pending_to_at: Mapped[int | None] = mapped_column(BigInteger)
    pending_offset: Mapped[int | None] = mapped_column(Integer)
    pending_limit: Mapped[int | None] = mapped_column(Integer)
    pending_total: Mapped[int | None] = mapped_column(Integer)
    last_success_run_id: Mapped[str | None] = mapped_column(String(36))
    last_success_at: Mapped[int | None] = mapped_column(BigInteger)
    last_cleanup_at: Mapped[int | None] = mapped_column(BigInteger)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    next_retry_at: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
