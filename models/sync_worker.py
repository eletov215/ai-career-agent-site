"""Persistent heartbeat for external synchronization workers."""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SyncWorker(Base):
    """One independently running synchronization worker process."""

    __tablename__ = "sync_workers"
    __table_args__ = (
        Index("idx_sync_workers_source_heartbeat", "source", "heartbeat_at"),
        Index("idx_sync_workers_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_run_id: Mapped[str | None] = mapped_column(String(36))
    started_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    heartbeat_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
