"""Add owner-scoped resume drafts, immutable versions, assets, and PDF metadata.

Revision ID: 20260812_0012
Revises: 20260812_0011
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260812_0012"
down_revision: Union[str, None] = "20260812_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resume_drafts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("completion_percent", sa.Integer(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "schema_version >= 1",
            name="ck_resume_drafts_schema_version",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_resume_drafts_revision"),
        sa.CheckConstraint(
            "completion_percent >= 0 AND completion_percent <= 100",
            name="ck_resume_drafts_completion_percent",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_resume_drafts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_drafts"),
    )
    op.create_index(
        "idx_resume_drafts_user_updated",
        "resume_drafts",
        ["user_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("draft_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("restored_from_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "schema_version >= 1",
            name="ck_resume_versions_schema_version",
        ),
        sa.CheckConstraint("version >= 1", name="ck_resume_versions_version"),
        sa.CheckConstraint(
            "draft_revision >= 1",
            name="ck_resume_versions_draft_revision",
        ),
        sa.CheckConstraint(
            "reason IN ('checkpoint', 'export', 'restore')",
            name="ck_resume_versions_reason",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["resume_drafts.id"],
            name="fk_resume_versions_draft_id_resume_drafts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_versions"),
        sa.UniqueConstraint(
            "draft_id",
            "version",
            name="uq_resume_versions_draft_version",
        ),
    )
    op.create_index(
        "idx_resume_versions_draft_created",
        "resume_versions",
        ["draft_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "resume_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("draft_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('photo', 'university_logo')",
            name="ck_resume_assets_kind",
        ),
        sa.CheckConstraint(
            "byte_size > 0 AND byte_size <= 2097152",
            name="ck_resume_assets_byte_size",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["resume_drafts.id"],
            name="fk_resume_assets_draft_id_resume_drafts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_resume_assets_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_assets"),
        sa.UniqueConstraint(
            "draft_id",
            "kind",
            "sha256",
            name="uq_resume_assets_draft_kind_sha256",
        ),
    )
    op.create_index(
        "idx_resume_assets_user_draft",
        "resume_assets",
        ["user_id", "draft_id"],
        unique=False,
    )

    op.create_table(
        "resume_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("draft_id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_resume_exports_version"),
        sa.CheckConstraint(
            "page_count >= 1 AND page_count <= 100",
            name="ck_resume_exports_page_count",
        ),
        sa.CheckConstraint(
            "byte_size > 0 AND byte_size <= 52428800",
            name="ck_resume_exports_byte_size",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["resume_drafts.id"],
            name="fk_resume_exports_draft_id_resume_drafts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["resume_versions.id"],
            name="fk_resume_exports_version_id_resume_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resume_exports"),
    )
    op.create_index(
        "idx_resume_exports_draft_created",
        "resume_exports",
        ["draft_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_resume_exports_draft_created", table_name="resume_exports")
    op.drop_table("resume_exports")
    op.drop_index("idx_resume_assets_user_draft", table_name="resume_assets")
    op.drop_table("resume_assets")
    op.drop_index("idx_resume_versions_draft_created", table_name="resume_versions")
    op.drop_table("resume_versions")
    op.drop_index("idx_resume_drafts_user_updated", table_name="resume_drafts")
    op.drop_table("resume_drafts")
