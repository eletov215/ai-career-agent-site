"""LEGAL-001 versioned AI consent foundation; production AI remains closed.

Revision ID: 20260922_0021
Revises: 20260917_0020
"""
from alembic import op
import sqlalchemy as sa

revision = "20260922_0021"
down_revision = "20260917_0020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("consent_type", sa.String(64), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(96), nullable=False),
        sa.Column("policy_hash", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(96), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("accepted_at", sa.BigInteger(), nullable=False),
        sa.Column("withdrawn_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id", "consent_type", "scope", "policy_version", "policy_hash",
            "provider", "purpose", "cycle", name="uq_ai_consents_policy_cycle"
        ),
        sa.CheckConstraint("cycle >= 1 AND revision >= 1", name="ck_ai_consents_versions"),
        sa.CheckConstraint("status IN ('accepted','withdrawn')", name="ck_ai_consents_status"),
        sa.CheckConstraint(
            "(status = 'accepted' AND withdrawn_at IS NULL) OR "
            "(status = 'withdrawn' AND withdrawn_at IS NOT NULL AND withdrawn_at >= accepted_at)",
            name="ck_ai_consents_withdrawal",
        ),
    )
    op.create_index("idx_ai_consents_owner_created", "ai_consents", ["user_id", "created_at"])
    op.create_index(
        "idx_ai_consents_owner_policy", "ai_consents",
        ["user_id", "consent_type", "scope", "policy_version", "provider", "purpose", "cycle"],
    )
    op.create_index(
        "uq_ai_consents_active_policy", "ai_consents",
        ["user_id", "consent_type", "scope", "policy_version", "policy_hash", "provider", "purpose"],
        unique=True,
        sqlite_where=sa.text("status = 'accepted'"),
        postgresql_where=sa.text("status = 'accepted'"),
    )


def downgrade():
    # Destructive for consent history. Use only with an explicit rollback decision
    # and a verified backup; downgrade cannot reconstruct accepted/withdrawn events.
    op.drop_index("uq_ai_consents_active_policy", table_name="ai_consents")
    op.drop_index("idx_ai_consents_owner_policy", table_name="ai_consents")
    op.drop_index("idx_ai_consents_owner_created", table_name="ai_consents")
    op.drop_table("ai_consents")
