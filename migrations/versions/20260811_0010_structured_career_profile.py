"""Add the owner-scoped structured career profile and immutable versions.

Revision ID: 20260811_0010
Revises: 20260811_0009
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260811_0010"
down_revision: Union[str, None] = "20260811_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "career_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("contacts_json", sa.Text(), nullable=False),
        sa.Column("goals_json", sa.Text(), nullable=False),
        sa.Column("geography_json", sa.Text(), nullable=False),
        sa.Column("salary_json", sa.Text(), nullable=False),
        sa.Column("skills_json", sa.Text(), nullable=False),
        sa.Column("employment_json", sa.Text(), nullable=False),
        sa.Column("achievements_json", sa.Text(), nullable=False),
        sa.Column("education_json", sa.Text(), nullable=False),
        sa.Column("languages_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("completion_percent", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "completion_percent >= 0 AND completion_percent <= 100",
            name="ck_career_profiles_completion_percent",
        ),
        sa.CheckConstraint(
            "schema_version >= 1",
            name="ck_career_profiles_schema_version",
        ),
        sa.CheckConstraint("version >= 1", name="ck_career_profiles_version"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_career_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_career_profiles"),
        sa.UniqueConstraint("user_id", name="uq_career_profiles_user_id"),
    )
    op.create_index(
        "idx_career_profiles_updated",
        "career_profiles",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "career_profile_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("changed_sections_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "schema_version >= 1",
            name="ck_career_profile_versions_schema_version",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_career_profile_versions_version",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["career_profiles.id"],
            name="fk_career_profile_versions_profile_id_career_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_career_profile_versions"),
        sa.UniqueConstraint(
            "profile_id",
            "version",
            name="uq_career_profile_versions_profile_version",
        ),
    )
    op.create_index(
        "idx_career_profile_versions_profile_created",
        "career_profile_versions",
        ["profile_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_career_profile_versions_profile_created",
        table_name="career_profile_versions",
    )
    op.drop_table("career_profile_versions")
    op.drop_index("idx_career_profiles_updated", table_name="career_profiles")
    op.drop_table("career_profiles")
