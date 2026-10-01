"""JOB-002 application tracker and immutable transition history.

Revision ID: 20261001_0022
Revises: 20260922_0021
"""
from alembic import op
import sqlalchemy as sa

revision = '20261001_0022'
down_revision = '20260922_0021'
branch_labels = None
depends_on = None
VALID = "'saved','preparing','submitted_user_reported','in_process_user_reported','closed'"


def upgrade():
    op.create_table('saved_vacancy_trackers',
        sa.Column('saved_vacancy_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('state', sa.String(32), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['saved_vacancy_id','user_id'], ['saved_vacancies.id','saved_vacancies.user_id'],
                                ondelete='CASCADE', name='fk_tracker_owned_saved_vacancy'),
        sa.UniqueConstraint('saved_vacancy_id','user_id', name='uq_tracker_saved_owner'),
        sa.CheckConstraint(f'state IN ({VALID})', name='ck_tracker_state'),
        sa.CheckConstraint('revision >= 1', name='ck_tracker_revision'))
    op.create_index('idx_tracker_owner_updated', 'saved_vacancy_trackers', ['user_id','updated_at'])
    op.create_table('saved_vacancy_tracker_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('saved_vacancy_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('from_state', sa.String(32), nullable=False),
        sa.Column('to_state', sa.String(32), nullable=False),
        sa.Column('event_revision', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['saved_vacancy_id','user_id'],
            ['saved_vacancy_trackers.saved_vacancy_id','saved_vacancy_trackers.user_id'],
            ondelete='CASCADE', name='fk_tracker_event_owned_tracker'),
        sa.CheckConstraint(f'from_state IN ({VALID})', name='ck_tracker_event_from_state'),
        sa.CheckConstraint(f'to_state IN ({VALID})', name='ck_tracker_event_to_state'),
        sa.CheckConstraint('from_state <> to_state', name='ck_tracker_event_changed'),
        sa.CheckConstraint('event_revision >= 1', name='ck_tracker_event_revision'),
        sa.UniqueConstraint('user_id','saved_vacancy_id','event_revision',
                            name='uq_tracker_event_owner_saved_revision'))
    op.create_index('idx_tracker_event_owner_saved_revision', 'saved_vacancy_tracker_events',
                    ['user_id','saved_vacancy_id','event_revision'])


def downgrade():
    op.drop_index('idx_tracker_event_owner_saved_revision', table_name='saved_vacancy_tracker_events')
    op.drop_table('saved_vacancy_tracker_events')
    op.drop_index('idx_tracker_owner_updated', table_name='saved_vacancy_trackers')
    op.drop_table('saved_vacancy_trackers')
