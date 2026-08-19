"""Add identifier-free privacy audit events for export/delete/retention controls.

Revision ID: 20260813_0013
Revises: 20260812_0012
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0013"
down_revision: Union[str, None] = "20260812_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "privacy_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("counts_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('data_exported', 'account_deleted', 'retention_cleanup')",
            name="ck_privacy_audit_events_type",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_privacy_audit_events"),
    )
    op.create_index(
        "idx_privacy_audit_events_created",
        "privacy_audit_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_privacy_audit_events_type_created",
        "privacy_audit_events",
        ["event_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_resume_assets_created",
        "resume_assets",
        ["created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_resume_assets_created", table_name="resume_assets")
    op.drop_index(
        "idx_privacy_audit_events_type_created",
        table_name="privacy_audit_events",
    )
    op.drop_index("idx_privacy_audit_events_created", table_name="privacy_audit_events")
    op.drop_table("privacy_audit_events")
