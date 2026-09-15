"""Additive SQLite + PostgreSQL migration, isolation, and policy contract tests."""
from pathlib import Path
import os,json
from uuid import uuid4
import pytest
from sqlalchemy import inspect,select,func,MetaData,Table,text
from database import create_database,upgrade_database,downgrade_database,current_revision
from models.ai import AIRuntimePolicy,AIPlanEntitlement,AIProviderState,AIBudgetBucket,AIUsageEvent
from repositories.ai import AIRepository
from services.ai.policy import DEFAULT_POLICY
from domain.ai import PROVIDER

TABLES={'ai_runtime_policies','ai_usage_events','ai_budget_buckets','ai_request_leases','ai_provider_states','ai_plan_entitlements','ai_user_plans'}

def test_sqlite_migration_round_trip(tmp_path):
    url=f'sqlite:///{tmp_path}/roundtrip.db';upgrade_database(url,'20260819_0014');db=create_database(url)
    before=set(inspect(db.engine).get_table_names())
    upgrade_database(url,"20260914_0015");assert current_revision(db.engine)=='20260914_0015'
    after=set(inspect(db.engine).get_table_names());assert after-before==TABLES
    with db.session() as s:
        assert json.loads(s.get(AIRuntimePolicy,1).policy_json)==DEFAULT_POLICY
        assert s.get(AIProviderState,PROVIDER).open_until==0
        assert s.scalar(select(func.count()).select_from(AIPlanEntitlement))==0
    upgrade_database(url,"20260914_0015");downgrade_database(url,'20260819_0014')
    assert set(inspect(db.engine).get_table_names())==before
    upgrade_database(url,"20260914_0015");assert current_revision(db.engine)=='20260914_0015';db.dispose()

def test_sqlite_alembic_no_model_drift(tmp_path):
    from alembic import command
    from database import alembic_config
    url=f'sqlite:///{tmp_path}/drift.db';upgrade_database(url);command.check(alembic_config(url))

@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'),reason='POSTGRES_TEST_URL required; dedicated CI provides PostgreSQL')
def test_postgresql_ai001_upgrade_atomicity_and_persistence():
    # Dedicated existing disposable CI database; never use DATABASE_URL here.
    from models import User
    from services.ai.registry import ContractRegistry
    from concurrent.futures import ThreadPoolExecutor
    import time
    from repositories.ai import AIAdmissionError
    url=os.environ['POSTGRES_TEST_URL'];upgrade_database(url);db=create_database(url)
    repo=AIRepository(db);v,original=repo.read_policy();now=int(time.time())
    user=str(uuid4())
    try:
        with db.session() as s,s.begin():s.add(User(id=user,status='active',email_verified_at=now,created_at=now,updated_at=now))
        changed={**original,'enabled':True,'kill_switch':False,'user_daily_budget_microrub':11840000,'max_user_concurrency':5,'max_global_concurrency':5,'pricing_checked_on':time.strftime('%Y-%m-%d',time.gmtime(now))}
        repo.update_policy(changed,expected_version=v,now=now)
        fixture,_=ContractRegistry().load('resume-analysis-en-01')
        def admit(n):
            try:return repo.admit(user_id=user,key_hash=f'{n:064x}',request_hash='f'*64,fixture=fixture,now=now)
            except AIAdmissionError as exc:return str(exc)
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(admit,range(4)))
        assert sum(not isinstance(r,str) for r in results)==1
        db.dispose();db=create_database(url)
        assert len(AIRepository(db).owner_usage(user))==1
        with db.session() as s:
            assert TABLES<=set(inspect(db.engine).get_table_names())
            assert s.get(AIRuntimePolicy,1).version>=v+1
    finally:
        from sqlalchemy import delete
        from models.ai import AIRequestLease
        repo=AIRepository(db)
        with db.session() as s,s.begin():
            ids=s.scalars(select(AIUsageEvent.id).where(AIUsageEvent.user_id==user)).all()
            if ids:s.execute(delete(AIRequestLease).where(AIRequestLease.id.in_(ids)))
            s.execute(delete(User).where(User.id==user))
        latest,_=repo.read_policy();repo.update_policy(original,expected_version=latest,now=now)
        db.dispose()
