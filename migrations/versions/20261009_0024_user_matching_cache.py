"""AI004-M04B: isolated owner-scoped dynamic matching cache and reports.

Revision ID: 20261009_0024
Revises: 20261002_0023

This additive migration is intended ONLY for disposable CI PostgreSQL/SQLite
during the draft PR. Do not apply to Neon, production or a shared database
without a separate owner-approved deployment/change window.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261009_0024"
down_revision = "20261002_0023"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_match_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_version_id", sa.String(36), sa.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved_vacancy_id", sa.String(36)),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("vacancy_identity_hash", sa.String(64), nullable=False),
        sa.Column("cache_key_hash", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("resume_hash", sa.String(64), nullable=False),
        sa.Column("vacancy_hash", sa.String(64), nullable=False),
        sa.Column("classification_version", sa.String(64), nullable=False),
        sa.Column("scoring_version", sa.String(64), nullable=False),
        sa.Column("usage_event_id", sa.String(36), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("result_hash", sa.String(64), nullable=False),
        sa.Column("result_seal", sa.String(64), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("id", "user_id", name="uq_user_match_report_id_owner"),
        sa.UniqueConstraint("user_id", "cache_key_hash", name="uq_user_match_report_owner_key"),
        sa.UniqueConstraint("user_id", "usage_event_id", name="uq_user_match_report_owner_usage"),
        sa.ForeignKeyConstraint(
            ["saved_vacancy_id", "user_id"], ["saved_vacancies.id", "saved_vacancies.user_id"],
            ondelete="CASCADE", name="fk_user_match_report_owned_vacancy",
        ),
        sa.CheckConstraint(
            "source_kind IN ('saved','search')", name="ck_user_match_report_source_kind",
        ),
        sa.CheckConstraint(
            "(source_kind = 'saved' AND saved_vacancy_id IS NOT NULL) OR "
            "(source_kind = 'search' AND saved_vacancy_id IS NULL)",
            name="ck_user_match_report_source_link",
        ),
    )
    op.create_index("idx_user_match_report_owner_created", "user_match_reports",
                    ["user_id", "created_at", "id"])

    op.create_table(
        "user_match_cache",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_version_id", sa.String(36), sa.ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved_vacancy_id", sa.String(36)),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("vacancy_identity_hash", sa.String(64), nullable=False),
        sa.Column("cache_key_hash", sa.String(64), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("operation_hash", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("report_id", sa.String(36)),
        sa.Column("lease_expires_at", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", "cache_key_hash", name="uq_user_match_cache_owner_key"),
        sa.ForeignKeyConstraint(
            ["saved_vacancy_id", "user_id"], ["saved_vacancies.id", "saved_vacancies.user_id"],
            ondelete="CASCADE", name="fk_user_match_cache_owned_vacancy",
        ),
        sa.ForeignKeyConstraint(
            ["report_id", "user_id"], ["user_match_reports.id", "user_match_reports.user_id"],
            ondelete="CASCADE", name="fk_user_match_cache_owned_report",
        ),
        sa.CheckConstraint(
            "state IN ('pending','ready','failed','unknown')",
            name="ck_user_match_cache_state",
        ),
        sa.CheckConstraint(
            "(state = 'ready' AND report_id IS NOT NULL) OR "
            "(state <> 'ready' AND report_id IS NULL)",
            name="ck_user_match_cache_ready_report",
        ),
        sa.CheckConstraint(
            "(source_kind = 'saved' AND saved_vacancy_id IS NOT NULL) OR "
            "(source_kind = 'search' AND saved_vacancy_id IS NULL)",
            name="ck_user_match_cache_source_link",
        ),
        sa.CheckConstraint("lease_expires_at >= 0", name="ck_user_match_cache_lease"),
    )
    op.create_index("idx_user_match_cache_owner_updated", "user_match_cache",
                    ["user_id", "updated_at", "id"])
    op.create_index("idx_user_match_cache_state_lease", "user_match_cache",
                    ["state", "lease_expires_at"])


def downgrade():
    # Destructive for new matching history. ONLY in disposable CI databases
    # or as part of an explicitly approved backup-and-restore recovery.
    op.drop_index("idx_user_match_cache_state_lease", table_name="user_match_cache")
    op.drop_index("idx_user_match_cache_owner_updated", table_name="user_match_cache")
    op.drop_table("user_match_cache")
    op.drop_index("idx_user_match_report_owner_created", table_name="user_match_reports")
    op.drop_table("user_match_reports")
