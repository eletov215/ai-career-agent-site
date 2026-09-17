"""JOB-001 owner snapshots; no AI activation and no legacy-browser backfill.

Revision ID: 20260917_0019
Revises: 20260916_0018
"""
from alembic import op
import sqlalchemy as sa
revision = '20260917_0019'
down_revision = '20260916_0018'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('saved_vacancies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_json', sa.Text(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('snapshot_version', sa.String(64), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('company', sa.Text(), nullable=False),
        sa.Column('location', sa.Text(), nullable=False),
        sa.Column('search_text', sa.Text(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('id', 'user_id', name='uq_saved_vacancy_id_owner'),
        sa.CheckConstraint('revision >= 1', name='ck_saved_vacancy_revision'))
    op.create_index('idx_saved_vacancy_owner_created', 'saved_vacancies', ['user_id', 'created_at', 'id'])
    op.create_table('saved_vacancy_sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('saved_vacancy_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column('external_id', sa.String(256), nullable=False),
        sa.Column('identity_hash', sa.String(64), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['saved_vacancy_id', 'user_id'], ['saved_vacancies.id', 'saved_vacancies.user_id'],
                                ondelete='CASCADE', name='fk_saved_source_owned_snapshot'),
        sa.UniqueConstraint('user_id', 'identity_hash', name='uq_saved_source_owner_identity'))
    op.create_index('idx_saved_source_snapshot', 'saved_vacancy_sources', ['saved_vacancy_id', 'user_id'])


def downgrade():
    # Destructive only for JOB-001; back up populated snapshots and notes first.
    op.drop_table('saved_vacancy_sources')
    op.drop_table('saved_vacancies')
