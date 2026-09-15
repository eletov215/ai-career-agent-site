"""Durable AI control plane, with no prompt/response or contact data columns."""
from __future__ import annotations
from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class AIRuntimePolicy(Base):
    __tablename__ = 'ai_runtime_policies'
    __table_args__ = (CheckConstraint('id = 1', name='ck_ai_policy_singleton'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

class AIUsageEvent(Base):
    __tablename__ = 'ai_usage_events'
    __table_args__ = (
        UniqueConstraint('user_id', 'idempotency_hash', name='uq_ai_usage_user_key'),
        CheckConstraint("status IN ('reserved','succeeded','failed','unknown')",name='ck_ai_usage_status'),
        CheckConstraint('reserved_microrub >= 0 AND charged_microrub >= 0', name='ck_ai_usage_money'),
        CheckConstraint('attempts >= 0', name='ck_ai_usage_attempts'),
        Index('idx_ai_usage_owner_created', 'user_id', 'created_at'),
        Index('idx_ai_usage_status_expiry', 'status', 'lease_expires_at'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'),nullable=False)
    idempotency_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64),nullable=False)
    task: Mapped[str] = mapped_column(String(32),nullable=False)
    language: Mapped[str] = mapped_column(String(2),nullable=False)
    fixture_id: Mapped[str] = mapped_column(String(64),nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32),nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer,nullable=False)
    input_rate: Mapped[int] = mapped_column(BigInteger,nullable=False)
    output_rate: Mapped[int] = mapped_column(BigInteger,nullable=False)
    day: Mapped[str] = mapped_column(String(10),nullable=False)
    month: Mapped[str] = mapped_column(String(7),nullable=False)
    status: Mapped[str] = mapped_column(String(16),nullable=False)
    reason: Mapped[str] = mapped_column(String(48),nullable=False)
    reserved_microrub: Mapped[int] = mapped_column(BigInteger,nullable=False)
    charged_microrub: Mapped[int] = mapped_column(BigInteger,nullable=False)
    cost_uncertain: Mapped[bool] = mapped_column(Boolean,nullable=False)
    attempts: Mapped[int] = mapped_column(Integer,nullable=False)
    input_tokens: Mapped[int] = mapped_column(BigInteger,nullable=False)
    output_tokens: Mapped[int] = mapped_column(BigInteger,nullable=False)
    commercial_reserved: Mapped[bool] = mapped_column(Boolean,nullable=False)
    commercial_action_consumed: Mapped[bool] = mapped_column(Boolean,nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger,nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger,nullable=False)
    lease_expires_at: Mapped[int] = mapped_column(BigInteger,nullable=False)

class AIBudgetBucket(Base):
    __tablename__ = 'ai_budget_buckets'
    __table_args__ = (
        CheckConstraint('spent_microrub >= 0 AND requests >= 0 AND successes >= 0',name='ck_ai_bucket_nonnegative'),
        Index('idx_ai_bucket_period', 'period'),
    )
    id: Mapped[str] = mapped_column(String(128),primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'),nullable=True)
    period: Mapped[str] = mapped_column(String(10),nullable=False)
    spent_microrub: Mapped[int] = mapped_column(BigInteger,nullable=False)
    requests: Mapped[int] = mapped_column(Integer,nullable=False)
    successes: Mapped[int] = mapped_column(Integer,nullable=False)

class AIRequestLease(Base):
    """Identifier-free capacity lease survives an account deletion until timeout.

    No FK to users/events, and no user identifier, so deletion cannot erase the
    global in-flight safety cap while an already dispatched request is running.
    """
    __tablename__ = 'ai_request_leases'
    id: Mapped[str] = mapped_column(String(36),primary_key=True)
    expires_at: Mapped[int] = mapped_column(BigInteger,nullable=False,index=True)

class AIProviderState(Base):
    __tablename__ = 'ai_provider_states'
    provider: Mapped[str] = mapped_column(String(32),primary_key=True)
    failures: Mapped[int] = mapped_column(Integer,nullable=False)
    open_until: Mapped[int] = mapped_column(BigInteger,nullable=False)
    probe_request_id: Mapped[str | None] = mapped_column(String(36))
    probe_until: Mapped[int] = mapped_column(BigInteger,nullable=False)

class AIPlanEntitlement(Base):
    __tablename__ = 'ai_plan_entitlements'
    __table_args__ = (CheckConstraint('monthly_limit >= 0',name='ck_ai_entitlement_limit'),)
    plan_key: Mapped[str] = mapped_column(String(32),primary_key=True)
    task: Mapped[str] = mapped_column(String(32),primary_key=True)
    monthly_limit: Mapped[int] = mapped_column(Integer,nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean,nullable=False)

class AIUserPlan(Base):
    __tablename__ = 'ai_user_plans'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    plan_key: Mapped[str] = mapped_column(String(32),nullable=False)
