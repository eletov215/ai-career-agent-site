"""Persistent provider synchronization run model."""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SyncRun(Base):
    """One attempt to synchronize vacancies from a source."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        Index("idx_sync_runs_source_started", "source", "started_at"),
        Index("idx_sync_runs_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    finished_at: Mapped[int | None] = mapped_column(BigInteger)
    target: Mapped[int | None] = mapped_column(Integer)
    processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cursor: Mapped[str | None] = mapped_column(Text)
    error_type: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
