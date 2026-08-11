"""Enforce one owned OAuth identity per provider and first-party user.

Revision ID: 20260811_0009
Revises: 20260810_0008
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260811_0009"
down_revision: Union[str, None] = "20260810_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _assert_no_owned_provider_duplicates() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            """
            SELECT user_id, provider, COUNT(*) AS connection_count
            FROM oauth_connections
            WHERE user_id IS NOT NULL
            GROUP BY user_id, provider
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicates is not None:
        raise RuntimeError(
            "AUTH-002 migration requires resolving duplicate owned provider connections first"
        )


def upgrade() -> None:
    # Existing unbound rows intentionally remain nullable. They can be claimed
    # only after an authenticated user proves control through a fresh provider
    # OAuth callback; no email-based auto-linking is performed.
    _assert_no_owned_provider_duplicates()
    with op.batch_alter_table("oauth_connections") as batch:
        batch.create_unique_constraint(
            "uq_oauth_connections_user_provider",
            ["user_id", "provider"],
        )


def downgrade() -> None:
    with op.batch_alter_table("oauth_connections") as batch:
        batch.drop_constraint(
            "uq_oauth_connections_user_provider",
            type_="unique",
        )
