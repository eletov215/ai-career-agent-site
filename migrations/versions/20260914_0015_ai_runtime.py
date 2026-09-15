"""AI-001 technical foundation. No real-data AI activation and no tariff seeds.

Revision ID: 20260914_0015
Revises: 20260819_0014
"""
from alembic import op
import sqlalchemy as sa
revision = "20260914_0015"
down_revision = "20260819_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ai_plan_entitlements',
    sa.Column('plan_key', sa.String(length=32), nullable=False),
    sa.Column('task', sa.String(length=32), nullable=False),
    sa.Column('monthly_limit', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.CheckConstraint('monthly_limit >= 0', name='ck_ai_entitlement_limit'),
    sa.PrimaryKeyConstraint('plan_key', 'task')
    )
    op.create_table('ai_provider_states',
    sa.Column('provider', sa.String(length=32), nullable=False),
    sa.Column('failures', sa.Integer(), nullable=False),
    sa.Column('open_until', sa.BigInteger(), nullable=False),
    sa.Column('probe_request_id', sa.String(length=36), nullable=True),
    sa.Column('probe_until', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('provider')
    )
    op.create_table('ai_request_leases',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('expires_at', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_request_leases_expires_at'), 'ai_request_leases', ['expires_at'], unique=False)
    op.create_table('ai_runtime_policies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('policy_json', sa.Text(), nullable=False),
    sa.Column('updated_at', sa.BigInteger(), nullable=False),
    sa.CheckConstraint('id = 1', name='ck_ai_policy_singleton'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ai_budget_buckets',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('period', sa.String(length=10), nullable=False),
    sa.Column('spent_microrub', sa.BigInteger(), nullable=False),
    sa.Column('requests', sa.Integer(), nullable=False),
    sa.Column('successes', sa.Integer(), nullable=False),
    sa.CheckConstraint('spent_microrub >= 0 AND requests >= 0 AND successes >= 0', name='ck_ai_bucket_nonnegative'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ai_bucket_period', 'ai_budget_buckets', ['period'], unique=False)
    op.create_table('ai_usage_events',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('idempotency_hash', sa.String(length=64), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('task', sa.String(length=32), nullable=False),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('fixture_id', sa.String(length=64), nullable=False),
    sa.Column('prompt_version', sa.String(length=32), nullable=False),
    sa.Column('policy_version', sa.Integer(), nullable=False),
    sa.Column('input_rate', sa.BigInteger(), nullable=False),
    sa.Column('output_rate', sa.BigInteger(), nullable=False),
    sa.Column('day', sa.String(length=10), nullable=False),
    sa.Column('month', sa.String(length=7), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('reason', sa.String(length=48), nullable=False),
    sa.Column('reserved_microrub', sa.BigInteger(), nullable=False),
    sa.Column('charged_microrub', sa.BigInteger(), nullable=False),
    sa.Column('cost_uncertain', sa.Boolean(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('input_tokens', sa.BigInteger(), nullable=False),
    sa.Column('output_tokens', sa.BigInteger(), nullable=False),
    sa.Column('commercial_reserved', sa.Boolean(), nullable=False),
    sa.Column('commercial_action_consumed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.Column('updated_at', sa.BigInteger(), nullable=False),
    sa.Column('lease_expires_at', sa.BigInteger(), nullable=False),
    sa.CheckConstraint("status IN ('reserved','succeeded','failed','unknown')", name='ck_ai_usage_status'),
    sa.CheckConstraint('attempts >= 0', name='ck_ai_usage_attempts'),
    sa.CheckConstraint('reserved_microrub >= 0 AND charged_microrub >= 0', name='ck_ai_usage_money'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'idempotency_hash', name='uq_ai_usage_user_key')
    )
    op.create_index('idx_ai_usage_owner_created', 'ai_usage_events', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_ai_usage_status_expiry', 'ai_usage_events', ['status', 'lease_expires_at'], unique=False)
    op.create_table('ai_user_plans',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('plan_key', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    control = sa.table("ai_runtime_policies", sa.column("id", sa.Integer), sa.column("version", sa.Integer), sa.column("policy_json", sa.Text), sa.column("updated_at", sa.BigInteger))
    op.bulk_insert(control, [{"id": 1, "version": 1, "policy_json": '{"attempt_timeout_seconds": 25, "circuit_cooldown_seconds": 60, "circuit_failures": 3, "commercial_enforcement_enabled": false, "enabled": false, "global_daily_budget_microrub": 1000000000, "global_daily_requests": 1000, "global_monthly_budget_microrub": 20000000000, "input_microrub_per_token": 500, "kill_switch": true, "lease_seconds": 90, "max_attempts": 2, "max_global_concurrency": 2, "max_input_tokens": 8000, "max_output_tokens": 1600, "max_user_concurrency": 1, "metadata_retention_days": 30, "output_microrub_per_token": 1200, "pricing_checked_on": "2026-09-14", "pricing_valid_days": 30, "retry_delay_seconds": 1, "total_timeout_seconds": 55, "user_daily_budget_microrub": 200000000, "user_daily_requests": 100}', "updated_at": 1789344000}])
    state = sa.table("ai_provider_states", sa.column("provider", sa.String), sa.column("failures", sa.Integer), sa.column("open_until", sa.BigInteger), sa.column("probe_until", sa.BigInteger))
    op.bulk_insert(state, [{"provider": "yandex-alice-ai-llm", "failures": 0, "open_until": 0, "probe_until": 0}])


def downgrade():
    op.drop_table("ai_user_plans")
    op.drop_table("ai_usage_events")
    op.drop_table("ai_request_leases")
    op.drop_table("ai_budget_buckets")
    op.drop_table("ai_plan_entitlements")
    op.drop_table("ai_provider_states")
    op.drop_table("ai_runtime_policies")
