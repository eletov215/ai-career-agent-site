"""Persistent bounded search snapshots for SEARCH-003."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SearchSnapshot(Base):
    """One stable multi-provider search result window.

    The snapshot stores only a query fingerprint.  The actual query parameters
    continue to travel in the URL and are revalidated against the fingerprint
    on every request.  Materialized items and provider cursors survive web
    process restarts until the bounded TTL expires.
    """

    __tablename__ = "search_snapshots"
    __table_args__ = (
        Index("idx_search_snapshots_fingerprint", "query_fingerprint"),
        Index("idx_search_snapshots_expires", "expires_at"),
        Index("idx_search_snapshots_status_updated", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    query_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_sources_json: Mapped[str] = mapped_column(Text, nullable=False)
    sort_code: Mapped[str] = mapped_column(String(32), nullable=False)
    page_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    provider_reported_total: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )
    known_unique_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    committed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_arrival_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cross_source_duplicate_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    cross_source_groups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_is_exact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extension_lease_until: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    sources = relationship(
        "SearchSnapshotSource",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    candidates = relationship(
        "SearchSnapshotCandidate",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    items = relationship(
        "SearchSnapshotItem",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SearchSnapshotSource(Base):
    """Per-provider cursor and total state for a snapshot."""

    __tablename__ = "search_snapshot_sources"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "source",
            name="uq_search_snapshot_sources_snapshot_source",
        ),
        Index("idx_search_snapshot_sources_snapshot", "snapshot_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("search_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    next_page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetched_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetched_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reported_total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_type: Mapped[str | None] = mapped_column(String(128))
    last_fetched_at: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    snapshot = relationship("SearchSnapshot", back_populates="sources")


class SearchSnapshotCandidate(Base):
    """One normalized provider publication fetched into a snapshot."""

    __tablename__ = "search_snapshot_candidates"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "source",
            "identity_key",
            name="uq_search_snapshot_candidates_identity",
        ),
        Index("idx_search_snapshot_candidates_snapshot", "snapshot_id"),
        Index(
            "idx_search_snapshot_candidates_snapshot_source",
            "snapshot_id",
            "source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("search_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_page: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    snapshot = relationship("SearchSnapshot", back_populates="candidates")


class SearchSnapshotItem(Base):
    """A deduplicated, stable ordinal exposed by pagination."""

    __tablename__ = "search_snapshot_items"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "ordinal",
            name="uq_search_snapshot_items_ordinal",
        ),
        UniqueConstraint(
            "snapshot_id",
            "stable_key",
            name="uq_search_snapshot_items_stable_key",
        ),
        Index("idx_search_snapshot_items_snapshot_ordinal", "snapshot_id", "ordinal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("search_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    stable_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_keys_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    snapshot = relationship("SearchSnapshot", back_populates="items")
