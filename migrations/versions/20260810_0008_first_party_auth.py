"""Add first-party password auth, revocable sessions, and one-time tokens.

Revision ID: 20260810_0008
Revises: 20260809_0007
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260810_0008"
down_revision: Union[str, None] = "20260809_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("password_hash", sa.Text(), nullable=True))
        batch.add_column(sa.Column("password_changed_at", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("last_login_at", sa.BigInteger(), nullable=True))

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("last_seen_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("revoked_at", sa.BigInteger(), nullable=True),
        sa.Column("revoke_reason", sa.String(length=64), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )
    op.create_index(
        "idx_auth_sessions_user_active",
        "auth_sessions",
        ["user_id", "revoked_at", "expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_auth_sessions_expires",
        "auth_sessions",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("consumed_at", sa.BigInteger(), nullable=True),
        sa.Column("consumed_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_auth_tokens_token_hash"),
    )
    op.create_index(
        "idx_auth_tokens_user_purpose",
        "auth_tokens",
        ["user_id", "purpose"],
        unique=False,
    )
    op.create_index(
        "idx_auth_tokens_expires",
        "auth_tokens",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_auth_tokens_consumed",
        "auth_tokens",
        ["consumed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_auth_tokens_consumed", table_name="auth_tokens")
    op.drop_index("idx_auth_tokens_expires", table_name="auth_tokens")
    op.drop_index("idx_auth_tokens_user_purpose", table_name="auth_tokens")
    op.drop_table("auth_tokens")

    op.drop_index("idx_auth_sessions_expires", table_name="auth_sessions")
    op.drop_index("idx_auth_sessions_user_active", table_name="auth_sessions")
    op.drop_table("auth_sessions")

    with op.batch_alter_table("users") as batch:
        batch.drop_column("last_login_at")
        batch.drop_column("password_changed_at")
        batch.drop_column("password_hash")
