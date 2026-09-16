"""AI-003 private reference interview; public real-data AI stays disabled.

Revision ID: 20260916_0017
Revises: 20260915_0016
"""
from alembic import op
import sqlalchemy as sa

revision = '20260916_0017'
down_revision = '20260915_0016'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('resume_interview_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('draft_id', sa.String(36), sa.ForeignKey('resume_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fixture_id', sa.String(64), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('contract_version', sa.String(64), nullable=False),
        sa.Column('source_json', sa.Text(), nullable=False),
        sa.Column('language', sa.String(2), nullable=False),
        sa.Column('origin', sa.String(16), nullable=False),
        sa.Column('operation_hash', sa.String(64), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('answers_json', sa.Text(), nullable=False),
        sa.Column('draft_revision', sa.Integer(), nullable=False),
        sa.Column('draft_content_hash', sa.String(64), nullable=False),
        sa.Column('confirmed_text', sa.Text(), nullable=True),
        sa.Column('confirmed_version_id', sa.String(36), sa.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('user_id', 'operation_hash', name='uq_interview_owner_operation'),
        sa.UniqueConstraint('draft_id', name='uq_interview_draft'),
        sa.CheckConstraint("origin = 'reference'", name='ck_interview_origin'),
        sa.CheckConstraint("status IN ('active', 'review', 'confirmed')", name='ck_interview_status'),
        sa.CheckConstraint("language IN ('ru', 'en')", name='ck_interview_language'),
        sa.CheckConstraint('revision >= 1 AND revision <= 60', name='ck_interview_revision'),
        sa.CheckConstraint('draft_revision >= 1', name='ck_interview_draft_revision'),
    )
    op.create_index('idx_interview_owner_updated', 'resume_interview_sessions', ['user_id', 'updated_at'])
    op.create_table('resume_interview_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('resume_interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('operation_hash', sa.String(64), nullable=False),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('session_id', 'revision', name='uq_interview_event_revision'),
        sa.UniqueConstraint('session_id', 'operation_hash', name='uq_interview_event_operation'),
        sa.CheckConstraint("kind IN ('started', 'answered', 'skipped', 'rewound', 'confirmed')", name='ck_interview_event_kind'),
        sa.CheckConstraint('revision >= 1 AND revision <= 60', name='ck_interview_event_revision'),
    )
    op.create_index('idx_interview_event_session', 'resume_interview_events', ['session_id', 'revision'])


def downgrade():
    # Keep PROF-003 drafts and their versions, including explicitly confirmed text.
    # Only AI-003 conversation history is removed. Take a verified backup first.
    op.drop_table('resume_interview_events')
    op.drop_table('resume_interview_sessions')
