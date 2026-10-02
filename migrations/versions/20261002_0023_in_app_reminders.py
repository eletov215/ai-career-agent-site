"""JOB-003 in-app reminder preferences and calendar dates.

Revision ID: 20261002_0023
Revises: 20261001_0022
"""
from alembic import op
import sqlalchemy as sa
revision = '20261002_0023'
down_revision = '20261001_0022'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('notification_preferences',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('in_app_reminders_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('revision', sa.Integer(), nullable=False), sa.Column('created_at', sa.BigInteger(), nullable=False), sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.CheckConstraint('revision >= 1', name='ck_notification_preference_revision'))
    op.create_table('saved_vacancy_reminders',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('saved_vacancy_id', sa.String(36), nullable=False), sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False), sa.Column('created_at', sa.BigInteger(), nullable=False), sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['saved_vacancy_id','user_id'], ['saved_vacancies.id','saved_vacancies.user_id'], ondelete='CASCADE', name='fk_reminder_owned_saved_vacancy'),
        sa.UniqueConstraint('user_id','saved_vacancy_id', name='uq_reminder_owner_saved'),
        sa.CheckConstraint('revision >= 1', name='ck_saved_vacancy_reminder_revision'))
    op.create_index('idx_reminder_owner_due_date', 'saved_vacancy_reminders', ['user_id','due_date'])


def downgrade():
    op.drop_index('idx_reminder_owner_due_date', table_name='saved_vacancy_reminders')
    op.drop_table('saved_vacancy_reminders'); op.drop_table('notification_preferences')
