"""AI-005 document foundation; public AI remains closed.

Revision ID: 20260917_0020
Revises: 20260917_0019
"""
from alembic import op
import sqlalchemy as sa
revision = '20260917_0020'
down_revision = '20260917_0019'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('cover_letters',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('saved_vacancy_id', sa.String(36), nullable=False),
        sa.Column('operation_hash', sa.String(64), nullable=False),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('source_json', sa.Text(), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('content_json', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('last_version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['saved_vacancy_id','user_id'], ['saved_vacancies.id','saved_vacancies.user_id'], ondelete='CASCADE', name='fk_letter_owned_vacancy'),
        sa.UniqueConstraint('id','user_id', name='uq_letter_id_owner'),
        sa.UniqueConstraint('user_id','operation_hash', name='uq_letter_owner_operation'),
        sa.CheckConstraint('revision >= 1 AND last_version >= 0', name='ck_letter_revisions'),
    )
    op.create_table('cover_letter_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('letter_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('content_json', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('origin', sa.String(32), nullable=False),
        sa.Column('evidence_json', sa.Text(), nullable=False),
        sa.Column('reviewed_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['letter_id','user_id'], ['cover_letters.id','cover_letters.user_id'], ondelete='CASCADE', name='fk_letter_version_owner'),
        sa.UniqueConstraint('letter_id','number', name='uq_letter_version_number'),
        sa.CheckConstraint('number >= 1', name='ck_letter_version_number'),
    )
    op.create_table('cover_letter_proposals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('letter_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('operation_hash', sa.String(64), nullable=False),
        sa.Column('request_hash', sa.String(64), nullable=False),
        sa.Column('base_revision', sa.Integer(), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('content_json', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('evidence_json', sa.Text(), nullable=False),
        sa.Column('origin', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['letter_id','user_id'], ['cover_letters.id','cover_letters.user_id'], ondelete='CASCADE', name='fk_letter_proposal_owner'),
        sa.UniqueConstraint('user_id','operation_hash', name='uq_letter_proposal_operation'),
        sa.CheckConstraint("status IN ('pending','accepted','rejected')", name="ck_letter_proposal_status"),
        sa.CheckConstraint('base_revision >= 1', name='ck_letter_proposal_revision'),
    )
    op.create_index('idx_letter_owner_vacancy','cover_letters',['user_id','saved_vacancy_id','created_at'])
    op.create_index('idx_letter_version_owner','cover_letter_versions',['user_id','letter_id'])
    op.create_index('idx_letter_proposal_owner','cover_letter_proposals',['user_id','letter_id'])


def downgrade():
    # Destructive for letter history; real backup/recovery approval is required.
    op.drop_table('cover_letter_proposals')
    op.drop_table('cover_letter_versions')
    op.drop_table('cover_letters')
