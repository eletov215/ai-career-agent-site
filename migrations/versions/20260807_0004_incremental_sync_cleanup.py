"""Add incremental sync checkpoints and vacancy lifecycle cleanup state.

Revision ID: 20260807_0004
Revises: 20260807_0003
Create Date: 2026-08-07
"""

from __future__ import annotations

import time
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260807_0004"
down_revision: Union[str, None] = "20260807_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = int(time.time())
    bind = op.get_bind()

    with op.batch_alter_table("vacancy_source_records") as batch:
        batch.add_column(sa.Column("source_modified_at", sa.Text(), nullable=True))
        batch.add_column(sa.Column("closed_at", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("closed_reason", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("last_seen_run_id", sa.String(length=36), nullable=True))

    op.create_index(
        "idx_vacancy_source_records_source_status_published",
        "vacancy_source_records",
        ["source", "source_status", "published_at"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_closed_at",
        "vacancy_source_records",
        ["closed_at"],
        unique=False,
    )

    op.create_table(
        "sync_checkpoints",
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("watermark_at", sa.BigInteger(), nullable=True),
        sa.Column("pending_from_at", sa.BigInteger(), nullable=True),
        sa.Column("pending_to_at", sa.BigInteger(), nullable=True),
        sa.Column("pending_offset", sa.Integer(), nullable=True),
        sa.Column("pending_limit", sa.Integer(), nullable=True),
        sa.Column("pending_total", sa.Integer(), nullable=True),
        sa.Column("last_success_run_id", sa.String(length=36), nullable=True),
        sa.Column("last_success_at", sa.BigInteger(), nullable=True),
        sa.Column("last_cleanup_at", sa.BigInteger(), nullable=True),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("next_retry_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("source"),
    )

    # Preserve the last successful SYNC-001 timestamp as the initial
    # incremental watermark. Sources without a successful run keep NULL and
    # receive one bounded initial snapshot before incremental windows begin.
    successful_rows = bind.execute(
        sa.text(
            """
            SELECT source, id, finished_at
              FROM (
                    SELECT
                        source,
                        id,
                        finished_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY source
                            ORDER BY finished_at DESC, id DESC
                        ) AS row_number
                      FROM sync_runs
                     WHERE status = 'succeeded'
                       AND finished_at IS NOT NULL
                   ) AS ranked_runs
             WHERE row_number = 1
            """
        )
    ).mappings()
    for row in successful_rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO sync_checkpoints (
                    source, watermark_at, pending_from_at, pending_to_at,
                    pending_offset, pending_limit, pending_total,
                    last_success_run_id, last_success_at, last_cleanup_at,
                    consecutive_failures, next_retry_at, created_at, updated_at
                ) VALUES (
                    :source, :watermark_at, NULL, NULL, NULL, NULL, NULL,
                    :run_id, :last_success_at, NULL, 0, NULL, :now, :now
                )
                """
            ),
            {
                "source": row["source"],
                "watermark_at": int(row["finished_at"]),
                "run_id": row["id"],
                "last_success_at": int(row["finished_at"]),
                "now": now,
            },
        )


def downgrade() -> None:
    op.drop_table("sync_checkpoints")
    op.drop_index(
        "idx_vacancy_source_records_closed_at",
        table_name="vacancy_source_records",
    )
    op.drop_index(
        "idx_vacancy_source_records_source_status_published",
        table_name="vacancy_source_records",
    )
    with op.batch_alter_table("vacancy_source_records") as batch:
        batch.drop_column("last_seen_run_id")
        batch.drop_column("closed_reason")
        batch.drop_column("closed_at")
        batch.drop_column("source_modified_at")
