"""AI-002 synthetic reports; no real-data activation or profile rewriting.

Revision ID: 20260915_0016
Revises: 20260914_0015
"""
from alembic import op
import sqlalchemy as sa

revision = "20260915_0016"
down_revision = "20260914_0015"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("resume_analysis_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fixture_id", sa.String(64), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("analysis_version", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("operation_hash", sa.String(64), nullable=False),
        sa.Column("usage_event_id", sa.String(36), nullable=True),
        sa.Column("source_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", "operation_hash", name="uq_analysis_owner_operation"),
        sa.UniqueConstraint("user_id", "fixture_id", "version", name="uq_analysis_owner_fixture_version"),
        sa.CheckConstraint("version >= 1", name="ck_analysis_version"),
        sa.CheckConstraint("origin IN ('reference', 'provider')", name="ck_analysis_origin"),
    )
    op.create_index("idx_analysis_owner_created", "resume_analysis_reports", ["user_id", "created_at"])
    op.create_table("resume_analysis_decisions",
        sa.Column("report_id", sa.String(36), sa.ForeignKey("resume_analysis_reports.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("recommendation_id", sa.String(16), primary_key=True),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("decision IN ('pending', 'accepted', 'rejected')", name="ck_analysis_decision"),
        sa.CheckConstraint("revision >= 0", name="ck_analysis_decision_revision"),
    )
    op.create_table("resume_analysis_review_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("resume_analysis_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_id", sa.String(16), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("report_id", "recommendation_id", "revision", name="uq_analysis_review_revision"),
        sa.CheckConstraint("decision IN ('pending', 'accepted', 'rejected')", name="ck_analysis_review_decision"),
        sa.CheckConstraint("revision >= 1", name="ck_analysis_review_revision"),
    )
    op.create_index("idx_analysis_review_report", "resume_analysis_review_events", ["report_id", "created_at"])

def downgrade():
    op.drop_table("resume_analysis_review_events")
    op.drop_table("resume_analysis_decisions")
    op.drop_table("resume_analysis_reports")
