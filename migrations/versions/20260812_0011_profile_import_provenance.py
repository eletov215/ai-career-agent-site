"""Add confirmed resume-import provenance to immutable profile versions.

Revision ID: 20260812_0011
Revises: 20260811_0010
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_0011"
down_revision: Union[str, None] = "20260811_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("career_profile_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_kind",
                sa.String(length=32),
                nullable=False,
                server_default="manual",
            )
        )
        batch_op.add_column(
            sa.Column(
                "provenance_json",
                sa.Text(),
                nullable=False,
                server_default="{}",
            )
        )
        batch_op.create_check_constraint(
            "ck_career_profile_versions_source_kind",
            "source_kind IN ('manual', 'resume_import')",
        )


def downgrade() -> None:
    with op.batch_alter_table("career_profile_versions") as batch_op:
        batch_op.drop_constraint(
            "ck_career_profile_versions_source_kind",
            type_="check",
        )
        batch_op.drop_column("provenance_json")
        batch_op.drop_column("source_kind")
