"""Move Trudvsem synchronization to an external worker process.

Revision ID: 20260807_0003
Revises: 20260804_0002
Create Date: 2026-08-07
"""

from __future__ import annotations

import time
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260807_0003"
down_revision: Union[str, None] = "20260804_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ACTIVE_RUN_PREDICATE = sa.text("status IN ('queued', 'running')")


def upgrade() -> None:
    bind = op.get_bind()
    now = int(time.time())

    # A process restart could leave historical in-memory worker runs marked as
    # running.  They cannot still be active during this migration, so close
    # them before enforcing one active run per source.
    bind.execute(
        sa.text(
            """
            UPDATE sync_runs
               SET status = 'failed',
                   finished_at = COALESCE(finished_at, :now),
                   error_type = COALESCE(error_type, 'WorkerRestarted'),
                   error_message = COALESCE(
                       error_message,
                       'Run abandoned before the SYNC-001 external worker migration.'
                   ),
                   updated_at = :now
             WHERE status = 'running'
            """
        ),
        {"now": now},
    )

    op.create_index(
        "uq_sync_runs_active_source",
        "sync_runs",
        ["source"],
        unique=True,
        postgresql_where=_ACTIVE_RUN_PREDICATE,
        sqlite_where=_ACTIVE_RUN_PREDICATE,
    )

    op.create_table(
        "sync_workers",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_run_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.BigInteger(), nullable=False),
        sa.Column("heartbeat_at", sa.BigInteger(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sync_workers_source_heartbeat",
        "sync_workers",
        ["source", "heartbeat_at"],
        unique=False,
    )
    op.create_index(
        "idx_sync_workers_status",
        "sync_workers",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_sync_workers_status", table_name="sync_workers")
    op.drop_index("idx_sync_workers_source_heartbeat", table_name="sync_workers")
    op.drop_table("sync_workers")
    op.drop_index("uq_sync_runs_active_source", table_name="sync_runs")
