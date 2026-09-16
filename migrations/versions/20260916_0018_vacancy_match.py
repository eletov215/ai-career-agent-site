"""AI-004 immutable synthetic match reports. No public AI activation.

Revision ID: 20260916_0018
Revises: 20260916_0017
"""
from alembic import op
import sqlalchemy as sa
revision = '20260916_0018'
down_revision = '20260916_0017'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('vacancy_match_series',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('fixture_id', sa.String(64), primary_key=True),
        sa.Column('last_version', sa.Integer(), nullable=False),
        sa.CheckConstraint('last_version >= 0', name='ck_match_series_version'),
    )
    op.create_table('vacancy_match_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fixture_id', sa.String(64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('origin', sa.String(16), nullable=False),
        sa.Column('language', sa.String(2), nullable=False),
        sa.Column('operation_hash', sa.String(64), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('candidate_hash', sa.String(64), nullable=False),
        sa.Column('vacancy_hash', sa.String(64), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.Column('source_version', sa.String(64), nullable=False),
        sa.Column('policy_version', sa.String(64), nullable=False),
        sa.Column('usage_event_id', sa.String(36), nullable=True),
        sa.Column('source_json', sa.Text(), nullable=False),
        sa.Column('result_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('user_id', 'operation_hash', name='uq_match_owner_operation'),
        sa.UniqueConstraint('user_id', 'fixture_id', 'version', name='uq_match_owner_fixture_version'),
        sa.CheckConstraint('version >= 1', name='ck_match_report_version'),
        sa.CheckConstraint("origin IN ('reference', 'provider')", name='ck_match_report_origin'),
        sa.CheckConstraint("language IN ('ru', 'en')", name='ck_match_report_language'),
    )
    op.create_index('idx_match_owner_created', 'vacancy_match_reports', ['user_id', 'created_at'])


def downgrade():
    # Destructive only for AI-004 reports/counters. Back up before downgrading.
    # Profile, resume, interview, vacancy cache and accounting tables survive.
    op.drop_table('vacancy_match_reports')
    op.drop_table('vacancy_match_series')
