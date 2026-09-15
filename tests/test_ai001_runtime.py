"""AI-001 regression suite: synthetic fixtures only, no paid provider requests."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import json, subprocess, sys
import pytest
from sqlalchemy import select, func, delete
from database import create_database
from models import Base, User
from models.ai import AIRuntimePolicy,AIProviderState,AIUsageEvent,AIBudgetBucket,AIRequestLease,AIPlanEntitlement,AIUserPlan
from domain.ai import AIRequest,ProviderResponse,ProviderError,PROVIDER,REAL_DATA_SUPPORTED,ProviderCall
from services.ai.policy import DEFAULT_POLICY, validate_policy, cost_microrub,rub_to_micro
from services.ai.registry import ContractRegistry,ContractError,validate_output,ROOT
from services.ai.service import AIService
from services.ai.settings import AISettings
from services.ai.provider import YandexAliceProvider,DeadlineTransport
from repositories.ai import AIRepository,AIAdmissionError

NOW=int(datetime(2026,9,14,12,tzinfo=timezone.utc).timestamp())

@pytest.fixture
def db(tmp_path):
    db=create_database(f'sqlite:///{tmp_path}/ai.db');Base.metadata.create_all(db.engine)
    with db.session() as s, s.begin():
        s.add(AIRuntimePolicy(id=1,version=1,policy_json=json.dumps(DEFAULT_POLICY),updated_at=NOW))
        s.add(AIProviderState(provider=PROVIDER,failures=0,open_until=0,probe_until=0))
    yield db
    db.dispose()

@pytest.fixture
def repo(db):return AIRepository(db)

@pytest.fixture
def user(db):
    uid=str(uuid4())
    with db.session() as s,s.begin():s.add(User(id=uid,email='fixture@example.invalid',normalized_email='fixture@example.invalid',status='active',email_verified_at=NOW,password_hash='test-only-hash',created_at=NOW,updated_at=NOW))
    return uid

def settings():
    return AISettings(True,False,True,'unit-test-placeholder','folder-test','gpt://folder-test/aliceai-llm/latest',NOW-86401)

def enable(repo,**changes):
    version,_=repo.read_policy()
    return repo.update_policy({'enabled':True,'kill_switch':False,**changes},expected_version=version,now=NOW)

class Fake:
    provider_id=PROVIDER
    def __init__(self,fixture='resume-analysis-en-01',sequence=None):
        self.calls=[];self.sequence=list(sequence) if sequence is not None else None
        self.body=(ROOT/f'evals/expected/reference/{fixture}.json').read_text()
    def generate(self,call):
        self.calls.append(call)
        value=self.sequence.pop(0) if self.sequence is not None else ProviderResponse(self.body,1000,300)
        if isinstance(value,Exception):raise value
        if callable(value):return value(call)
        return value

def service(repo,provider,**kwargs):
    return AIService(repo,settings(),fingerprint_key='unit-test-only-fingerprint',provider=provider,clock=lambda:NOW,sleep=lambda _:None,**kwargs)

def req(user,fixture='resume-analysis-en-01',key=None):return AIRequest(user,key or str(uuid4()),fixture)

def event(db,rid):
    with db.session() as s:return s.get(AIUsageEvent,rid)

@pytest.mark.parametrize('fixture',[p.stem for p in (ROOT/'evals/fixtures/cases').glob('*.json')])
def test_all_eight_pinned_contracts_round_trip(repo,user,db,fixture):
    enable(repo);fake=Fake(fixture);result=service(repo,fake).generate(req(user,fixture))
    assert result.status=='succeeded' and result.content and not result.commercial_action_consumed
    assert len(fake.calls)==1
    row=event(db,result.request_id)
    assert row.status=='succeeded' and row.charged_microrub==860000 and not row.cost_uncertain
    assert row.input_tokens==1000 and row.output_tokens==300

@pytest.mark.parametrize('settings_value,reason',[
    (AISettings(),'runtime_not_activated'),(replace(settings(),enabled=False),'runtime_not_activated'),
    (replace(settings(),kill_switch=True),'runtime_not_activated'),
    (replace(settings(),synthetic_access_enabled=False),'synthetic_access_disabled'),
    (replace(settings(),api_key=''),'provider_not_configured'),
    (replace(settings(),model_uri='gpt://folder-test/other/latest'),'provider_not_configured'),
    (replace(settings(),no_logging_disabled_at=None),'no_logging_wait'),
    (replace(settings(),no_logging_disabled_at=NOW-80000),'no_logging_wait'),
    (replace(settings(),no_logging_disabled_at=NOW+1),'no_logging_wait')])
def test_environment_gates_do_not_call_provider(repo,user,settings_value,reason):
    enable(repo);fake=Fake();s=AIService(repo,settings_value,fingerprint_key='secret',provider=fake,clock=lambda:NOW)
    assert s.generate(req(user)).reason==reason and not fake.calls
    assert s.public_status()['mode']=='manual'

@pytest.mark.parametrize('change',[{'enabled':False},{'kill_switch':True},{'pricing_checked_on':'2026-08-01'},{'pricing_checked_on':'2026-09-15'}])
def test_db_control_or_stale_price_blocks(repo,user,change):
    enable(repo,**change);f=Fake();res=service(repo,f).generate(req(user))
    assert res.status=='manual' and not f.calls

def test_no_arbitrary_personal_data_entry(repo,user):
    enable(repo);f=Fake();s=service(repo,f)
    assert REAL_DATA_SUPPORTED is False
    assert s.generate({'user_id':user,'resume':'arbitrary'}).status=='manual'
    for fixture in ('../../secrets','resume-analysis-en-99','real-resume','/etc/passwd'):
        assert s.generate(req(user,fixture)).status=='manual'
    assert not f.calls

def test_idempotency_prevents_duplicate_charge_and_calls(repo,user,db):
    enable(repo);f=Fake();s=service(repo,f);r=req(user);a=s.generate(r);b=s.generate(r)
    assert a.status=='succeeded' and b.status=='duplicate' and b.request_id==a.request_id
    assert len(f.calls)==1
    collision=s.generate(req(user,'cover-letter-en-01',r.idempotency_key))
    assert collision.reason=='idempotency_conflict' and len(f.calls)==1

def test_user_isolation(repo,user,db):
    enable(repo);other=str(uuid4())
    with db.session() as s,s.begin():s.add(User(id=other,status='active',email_verified_at=NOW,created_at=NOW,updated_at=NOW))
    f=Fake();svc=service(repo,f)
    a=svc.generate(req(user,key='same-key-00001'));b=svc.generate(req(other,key='same-key-00001'))
    assert a.request_id!=b.request_id and len(f.calls)==2
    assert len(repo.owner_usage(user))==1 and len(repo.owner_usage(other))==1

@pytest.mark.parametrize('active,verified',[(False,True),(True,False)])
def test_verified_account_required(repo,user,db,active,verified):
    enable(repo)
    with db.session() as s,s.begin():
        u=s.get(User,user);u.status='active' if active else 'pending';u.email_verified_at=NOW if verified else None
    f=Fake();assert service(repo,f).generate(req(user)).reason=='verified_account_required';assert not f.calls

@pytest.mark.parametrize('control',[{'user_daily_budget_microrub':1},{'global_daily_budget_microrub':1,'user_daily_budget_microrub':1},{'global_monthly_budget_microrub':1,'global_daily_budget_microrub':1,'user_daily_budget_microrub':1}])
def test_cost_admission_fail_closed(repo,user,control):
    enable(repo,**control);f=Fake();assert service(repo,f).generate(req(user)).reason=='budget_exhausted';assert not f.calls

def test_request_cap(repo,user):
    enable(repo,user_daily_requests=1);f=Fake();svc=service(repo,f)
    assert svc.generate(req(user)).status=='succeeded'
    assert svc.generate(req(user)).reason=='request_limit' and len(f.calls)==1

def test_retry_only_declared_statuses_and_cost_settlement(repo,user,db):
    enable(repo);ok=ProviderResponse(Fake().body,1000,300)
    f=Fake(sequence=[ProviderError('upstream_error',retryable=True,unknown=True),ok])
    res=service(repo,f).generate(req(user));row=event(db,res.request_id)
    assert res.status=='succeeded' and len(f.calls)==2 and row.attempts==2
    assert row.cost_uncertain and row.charged_microrub==5920000+860000

@pytest.mark.parametrize('code',['timeout_unknown','transport_unknown','permission_denied','invalid_request','refusal','invalid_envelope'])
def test_nonretryable_failures_never_get_second_attempt(repo,user,code):
    enable(repo);f=Fake(sequence=[ProviderError(code,retryable=True)])
    r=service(repo,f).generate(req(user));assert r.status=='manual' and len(f.calls)==1 and not r.commercial_action_consumed

def test_unknown_outcome_holds_cost_and_key(repo,user,db):
    enable(repo);f=Fake(sequence=[ProviderError('timeout_unknown')]);svc=service(repo,f);request=req(user)
    r=svc.generate(request);row=event(db,r.request_id)
    assert row.status=='unknown' and row.cost_uncertain and row.charged_microrub==5920000
    assert svc.generate(request).status=='duplicate' and len(f.calls)==1

@pytest.mark.parametrize('body',['not json','{}','{"bad":null}','{"x":NaN}','{"subject":"x","subject":"y"}'])
def test_invalid_output_refunds_only_user_entitlement_not_upstream(repo,user,db,body):
    enable(repo);f=Fake(sequence=[ProviderResponse(body,1000,300)])
    res=service(repo,f).generate(req(user));row=event(db,res.request_id)
    assert res.reason=='schema_failure' and row.status=='failed' and row.charged_microrub==860000
    assert not row.commercial_action_consumed and len(f.calls)==1

def test_usage_overrun_kills_policy_without_understating_spend(repo,user,db):
    enable(repo);f=Fake(sequence=[ProviderResponse(Fake().body,9000,300)])
    res=service(repo,f).generate(req(user));row=event(db,res.request_id)
    assert res.reason=='usage_limit_overrun' and row.charged_microrub==4860000
    assert repo.read_policy()[1]['kill_switch']

def test_missing_usage_retains_conservative_charge(repo,user,db):
    enable(repo);f=Fake(sequence=[ProviderResponse(Fake().body,None,None)])
    r=service(repo,f).generate(req(user));row=event(db,r.request_id)
    assert row.cost_uncertain and row.charged_microrub==5920000

def test_settlement_failure_hides_result_and_retains_reservation(repo,user,db,monkeypatch):
    enable(repo);f=Fake()
    monkeypatch.setattr(repo,'settle',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('not for user')))
    r=service(repo,f).generate(req(user));assert r.reason=='ledger_unavailable' and r.content is None
    row=event(db,r.request_id);assert row.status=='reserved' and row.charged_microrub==11840000

def test_kill_switch_before_retry(repo,user,db):
    enable(repo)
    def fail(call):
        v,_=repo.read_policy();repo.update_policy({'kill_switch':True},expected_version=v,now=NOW)
        raise ProviderError('rate_limited',retryable=True,unknown=False)
    f=Fake(sequence=[fail]);r=service(repo,f).generate(req(user))
    assert len(f.calls)==1 and r.reason=='runtime_not_activated' and event(db,r.request_id).charged_microrub==0

def test_atomic_concurrency_and_budget_reservation(repo,user):
    enable(repo,max_user_concurrency=5,max_global_concurrency=5,user_daily_budget_microrub=11840000)
    fixture,_=ContractRegistry().load('resume-analysis-en-01')
    def admit(n):
        try:return repo.admit(user_id=user,key_hash=f'{n:064x}',request_hash='a'*64,fixture=fixture,now=NOW)
        except AIAdmissionError as e:return str(e)
    with ThreadPoolExecutor(max_workers=5) as pool:r=list(pool.map(admit,range(5)))
    assert sum(not isinstance(a,str) for a in r)==1 and r.count('budget_exhausted')==4

def test_recovery_survives_process_restart_and_preserves_reservation(repo,user,db):
    enable(repo);fixture,_=ContractRegistry().load('resume-analysis-en-01')
    a=repo.admit(user_id=user,key_hash='a'*64,request_hash='b'*64,fixture=fixture,now=NOW)
    restarted=AIRepository(db)
    assert restarted.recover(now=NOW+100)==1
    row=event(db,a.request_id);assert row.status=='unknown' and row.charged_microrub==11840000
    assert restarted.admit(user_id=user,key_hash='a'*64,request_hash='b'*64,fixture=fixture,now=NOW+100).duplicate

def test_circuit_opens_and_allows_only_one_probe(repo,user,db):
    enable(repo,circuit_failures=1,max_user_concurrency=5,max_global_concurrency=5)
    f=Fake(sequence=[ProviderError('timeout_unknown')]);service(repo,f).generate(req(user))
    assert service(repo,Fake()).generate(req(user)).reason=='provider_circuit_open'
    fixture,_=ContractRegistry().load('resume-analysis-en-01')
    a=repo.admit(user_id=user,key_hash='a'*64,request_hash='b'*64,fixture=fixture,now=NOW+61)
    with pytest.raises(AIAdmissionError,match='provider_circuit_open'):
        repo.admit(user_id=user,key_hash='c'*64,request_hash='d'*64,fixture=fixture,now=NOW+61)
    repo.settle(a.request_id,status='succeeded',reason='ok',cost=10,uncertain=False,input_tokens=0,output_tokens=0,provider_failed=False,now=NOW+62)
    with db.session() as s:
        state=s.get(AIProviderState,PROVIDER);assert state.open_until==0 and state.probe_until==0

def test_global_counters_survive_account_deletion_inflight(repo,user,db):
    enable(repo);fixture,_=ContractRegistry().load('resume-analysis-en-01')
    a=repo.admit(user_id=user,key_hash='a'*64,request_hash='b'*64,fixture=fixture,now=NOW)
    with db.session() as s,s.begin():s.execute(delete(User).where(User.id==user))
    with db.session() as s:
        assert not s.scalars(select(AIUsageEvent)).all()
        assert s.get(AIRequestLease,a.request_id) is not None
        assert s.get(AIBudgetBucket,'global:month:2026-09').spent_microrub==11840000
    assert not repo.settle(a.request_id,status='succeeded',reason='ok',cost=10,uncertain=False,input_tokens=0,output_tokens=0,provider_failed=False,now=NOW+10)
    with db.session() as s:
        assert s.get(AIBudgetBucket,'global:month:2026-09').spent_microrub==11840000
        assert s.get(AIRequestLease,a.request_id) is None

def test_entitlements_separate_and_not_seeded(repo,user,db):
    enable(repo,commercial_enforcement_enabled=True);f=Fake();svc=service(repo,f)
    assert svc.generate(req(user)).reason=='entitlement_unavailable'
    with db.session() as s,s.begin():
        s.add(AIPlanEntitlement(plan_key='standard',task='resume_analysis',monthly_limit=1,enabled=True))
        s.add(AIUserPlan(user_id=user,plan_key='standard'))
    f=Fake(sequence=[ProviderResponse('{}',100,10),ProviderResponse(Fake().body,100,10)]);svc=service(repo,f)
    assert not svc.generate(req(user)).commercial_action_consumed
    assert svc.generate(req(user)).commercial_action_consumed
    assert svc.generate(req(user)).reason=='commercial_quota_exhausted'

def test_retention_does_not_reset_current_month_spend(repo,user,db):
    enable(repo,metadata_retention_days=1);service(repo,Fake()).generate(req(user))
    counts=repo.cleanup(now=NOW+2*86400);assert counts['events_deleted']==1
    with db.session() as s:assert s.get(AIBudgetBucket,'global:month:2026-09').spent_microrub==860000

def test_policy_is_mutable_versioned_and_rejects_invalid_values(repo):
    v,p=repo.read_policy();repo.update_policy({'user_daily_budget_microrub':250000000},expected_version=v,now=NOW)
    assert repo.read_policy()[0]==2
    with pytest.raises(AIAdmissionError):repo.update_policy({'kill_switch':True},expected_version=1,now=NOW)
    for changes in ({'max_attempts':3},{'max_attempts':True},{'max_user_concurrency':3},{'global_daily_budget_microrub':-1},{'unknown':True},{'pricing_checked_on':'invalid'}):
        with pytest.raises(ValueError):validate_policy({**DEFAULT_POLICY,**changes})

@pytest.mark.parametrize('value',['-1','1e3','nan','Infinity','0','2.0000001'])
def test_invalid_money_rejected(value):
    with pytest.raises(ValueError):rub_to_micro(value)

def test_money_has_no_binary_rounding():
    assert rub_to_micro('103.104')==103104000
    assert cost_microrub(4000,1200,DEFAULT_POLICY)==3440000

def test_no_secret_in_repr_or_public_state(repo):
    s=settings();assert 'unit-test-placeholder' not in repr(s)
    assert 'resume secret' not in repr(ProviderResponse('resume secret',1,1))
    a=service(repo,Fake()).public_status();serialized=json.dumps(a)
    for term in ('api_key','folder','user_id','unit-test-placeholder'):assert term not in serialized

def test_transport_headers_fixed_and_content_not_logged():
    seen=[]
    def transport(payload,timeout):
        seen.append(payload)
        return {'ok':True,'envelope':{'usage':{'prompt_tokens':0,'completion_tokens':0},'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}}
    p=YandexAliceProvider(settings(),transport=transport)
    result=p.generate(ProviderCall('request','cover_letter','en',[{'role':'user','content':'fixture'}],{},100,5))
    assert result.input_tokens==0 and result.output_tokens==0
    assert seen[0]['headers']['x-data-logging-enabled']=='false'
    assert seen[0]['headers']['Authorization']=='Api-Key unit-test-placeholder'
    assert seen[0]['body']['response_format']['type']=='json_schema' and seen[0]['body']['stream'] is False
    assert 'tools' not in seen[0]['body'] and 'files' not in seen[0]['body']

def test_hard_deadline_terminates_subprocess(monkeypatch):
    import services.ai.provider as p
    monkeypatch.setenv('APP_ENV','development')
    class Process:
        returncode=1
        killed=False
        def communicate(self,*args,**kwargs):
            if not self.killed:raise subprocess.TimeoutExpired('private-worker',1)
            return b'',b''
        def kill(self):self.killed=True
    proc=Process();monkeypatch.setattr(p.subprocess,'Popen',lambda *a,**k:proc)
    with pytest.raises(ProviderError,match='timeout_unknown'):DeadlineTransport()({},.01)
    assert proc.killed

def test_deadline_transport_refuses_test_environment(monkeypatch):
    monkeypatch.setenv('APP_ENV','test')
    with pytest.raises(ProviderError,match='configuration'):DeadlineTransport()({},1)

def test_registry_detects_file_tamper(tmp_path):
    import shutil
    for folder in ('prompts','schemas','services/ai'):
        shutil.copytree(ROOT/folder,tmp_path/folder,dirs_exist_ok=True)
    p=tmp_path/'prompts/ai/grounded-v2.6.1/resume-analysis-en-01.json';p.write_text('{}')
    with pytest.raises(ContractError):ContractRegistry(tmp_path).load('resume-analysis-en-01')

def test_settings_malformed_secret_and_time_are_safe():
    for env in ({'AI_ENABLED':'maybe'},{'AI_YANDEX_API_KEY':'secret\nvalue'},{'AI_NO_LOGGING_DISABLED_AT':'2026-09-14'}):
        with pytest.raises(ValueError) as e:AISettings.from_environ(env)
        assert 'secret\nvalue' not in str(e.value)


def test_technical_success_does_not_consume_future_commercial_quota(repo,user,db):
    enable(repo);svc=service(repo,Fake())
    assert svc.generate(req(user)).status=='succeeded'
    enable(repo,commercial_enforcement_enabled=True)
    with db.session() as session,session.begin():
        session.add(AIPlanEntitlement(plan_key='standard',task='resume_analysis',monthly_limit=1,enabled=True))
        session.add(AIUserPlan(user_id=user,plan_key='standard'))
    assert svc.generate(req(user)).commercial_action_consumed
    assert svc.generate(req(user)).reason=='commercial_quota_exhausted'


def test_input_bound_is_checked_inside_atomic_admission(repo,user):
    enable(repo,max_input_tokens=1)
    fake=Fake();res=service(repo,fake).generate(req(user))
    assert res.reason=='input_limit' and not fake.calls
    assert not repo.owner_usage(user)


def test_http_child_blocks_redirects_and_never_reads_error_body(monkeypatch):
    from services.ai import _http_worker as child
    seen=[]
    class Response:
        status_code=302
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,**kwargs):raise AssertionError('Never read error body')
    class Session:
        trust_env=True
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kw):seen.append((url,kw,self.trust_env));return Response()
    monkeypatch.setattr(child.requests,'Session',Session)
    result=child.perform({'headers':{'x-data-logging-enabled':'false'},'body':{},'timeout':2})
    assert not result['ok'] and not result['retryable'] and result['unknown']
    assert seen[0][0]==child.ENDPOINT and not seen[0][1]['allow_redirects'] and seen[0][2] is False
