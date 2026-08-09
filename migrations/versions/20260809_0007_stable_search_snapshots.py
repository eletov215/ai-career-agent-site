"""Add bounded persistent search snapshots for SEARCH-003.

Revision ID: 20260809_0007
Revises: 20260809_0006
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260809_0007"
down_revision: Union[str, None] = "20260809_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("selected_sources_json", sa.Text(), nullable=False),
        sa.Column("sort_code", sa.String(length=32), nullable=False),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_reported_total", sa.BigInteger(), nullable=False),
        sa.Column("known_unique_total", sa.Integer(), nullable=False),
        sa.Column("committed_count", sa.Integer(), nullable=False),
        sa.Column("late_arrival_count", sa.Integer(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("cross_source_duplicate_count", sa.Integer(), nullable=False),
        sa.Column("cross_source_groups", sa.Integer(), nullable=False),
        sa.Column("total_is_exact", sa.Boolean(), nullable=False),
        sa.Column("bounded", sa.Boolean(), nullable=False),
        sa.Column("extension_lease_until", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_search_snapshots_fingerprint",
        "search_snapshots",
        ["query_fingerprint"],
        unique=False,
    )
    op.create_index(
        "idx_search_snapshots_expires",
        "search_snapshots",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_search_snapshots_status_updated",
        "search_snapshots",
        ["status", "updated_at"],
        unique=False,
    )

    op.create_table(
        "search_snapshot_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("next_page", sa.Integer(), nullable=False),
        sa.Column("fetched_pages", sa.Integer(), nullable=False),
        sa.Column("fetched_items", sa.Integer(), nullable=False),
        sa.Column("reported_total", sa.BigInteger(), nullable=False),
        sa.Column("exhausted", sa.Boolean(), nullable=False),
        sa.Column("bounded", sa.Boolean(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("last_error_type", sa.String(length=128), nullable=True),
        sa.Column("last_fetched_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["search_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "source",
            name="uq_search_snapshot_sources_snapshot_source",
        ),
    )
    op.create_index(
        "idx_search_snapshot_sources_snapshot",
        "search_snapshot_sources",
        ["snapshot_id"],
        unique=False,
    )

    op.create_table(
        "search_snapshot_candidates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("identity_key", sa.String(length=128), nullable=False),
        sa.Column("provider_page", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["search_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "source",
            "identity_key",
            name="uq_search_snapshot_candidates_identity",
        ),
    )
    op.create_index(
        "idx_search_snapshot_candidates_snapshot",
        "search_snapshot_candidates",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        "idx_search_snapshot_candidates_snapshot_source",
        "search_snapshot_candidates",
        ["snapshot_id", "source"],
        unique=False,
    )

    op.create_table(
        "search_snapshot_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("stable_key", sa.String(length=128), nullable=False),
        sa.Column("source_keys_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["search_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "ordinal",
            name="uq_search_snapshot_items_ordinal",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "stable_key",
            name="uq_search_snapshot_items_stable_key",
        ),
    )
    op.create_index(
        "idx_search_snapshot_items_snapshot_ordinal",
        "search_snapshot_items",
        ["snapshot_id", "ordinal"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_search_snapshot_items_snapshot_ordinal",
        table_name="search_snapshot_items",
    )
    op.drop_table("search_snapshot_items")

    op.drop_index(
        "idx_search_snapshot_candidates_snapshot_source",
        table_name="search_snapshot_candidates",
    )
    op.drop_index(
        "idx_search_snapshot_candidates_snapshot",
        table_name="search_snapshot_candidates",
    )
    op.drop_table("search_snapshot_candidates")

    op.drop_index(
        "idx_search_snapshot_sources_snapshot",
        table_name="search_snapshot_sources",
    )
    op.drop_table("search_snapshot_sources")

    op.drop_index(
        "idx_search_snapshots_status_updated",
        table_name="search_snapshots",
    )
    op.drop_index(
        "idx_search_snapshots_expires",
        table_name="search_snapshots",
    )
    op.drop_index(
        "idx_search_snapshots_fingerprint",
        table_name="search_snapshots",
    )
    op.drop_table("search_snapshots")
