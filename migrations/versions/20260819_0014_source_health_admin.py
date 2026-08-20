"""Add safe persistent provider health state for SEARCH-005.

Revision ID: 20260819_0014
Revises: 20260813_0013
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_0014"
down_revision: Union[str, None] = "20260813_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_health_states",
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("availability", sa.String(length=32), nullable=False),
        sa.Column("configured", sa.Boolean(), nullable=False),
        sa.Column("last_attempt_at", sa.BigInteger(), nullable=True),
        sa.Column("last_success_at", sa.BigInteger(), nullable=True),
        sa.Column("last_failure_at", sa.BigInteger(), nullable=True),
        sa.Column("last_latency_ms", sa.Integer(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("cache_observed_at", sa.BigInteger(), nullable=True),
        sa.Column("cache_item_count", sa.Integer(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "availability IN ('unknown','available','cached','degraded','auth_required','temporarily_unavailable','disabled')",
            name="ck_source_health_states_availability",
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_source_health_states_failures_nonnegative",
        ),
        sa.CheckConstraint(
            "last_latency_ms IS NULL OR last_latency_ms >= 0",
            name="ck_source_health_states_latency_nonnegative",
        ),
        sa.CheckConstraint(
            "cache_item_count IS NULL OR cache_item_count >= 0",
            name="ck_source_health_states_cache_count_nonnegative",
        ),
        sa.PrimaryKeyConstraint("provider", name="pk_source_health_states"),
    )
    op.create_index("idx_source_health_updated", "source_health_states", ["updated_at"], unique=False)
    op.create_index("idx_source_health_availability", "source_health_states", ["availability"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_source_health_availability", table_name="source_health_states")
    op.drop_index("idx_source_health_updated", table_name="source_health_states")
    op.drop_table("source_health_states")
