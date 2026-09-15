"""AI-002 reconstructed candidate: no live requests, credentials or user resumes."""
from dataclasses import replace
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import copy
import json
import pytest
from sqlalchemy import select,func,delete
from database import create_database,upgrade_database
from models import Base,User,CareerProfile,ResumeDraft
from models.ai import AIRuntimePolicy,AIProviderState,AIUsageEvent
from models.resume_analysis import ResumeAnalysisReport,ResumeAnalysisDecision,ResumeAnalysisReviewEvent
from repositories.ai import AIRepository
from repositories.resume_analysis import ResumeAnalysisRepository
from repositories.privacy import PrivacyRepository
from services.ai.service import AIService
from services.ai.settings import AISettings
from services.ai.policy import DEFAULT_POLICY
from services.ai.registry import ContractRegistry,ContractError,ROOT
from services.ai.analysis_validation import validate_analysis
from services.resume_analysis import ResumeAnalysisService
from domain.ai import AIRequest,ProviderResponse,ProviderError,PROVIDER
from domain.resume_analysis import AnalysisRequest,AnalysisError

NOW=int(datetime(2026,9,15,12,tzinfo=timezone.utc).timestamp())

@pytest.fixture
def env(tmp_path):
    db=create_database(f'sqlite:///{tmp_path}/analysis.db');Base.metadata.create_all(db.engine)
    user=str(uuid4());other=str(uuid4())
    with db.session() as s,s.begin():
        for uid in (user,other):s.add(User(id=uid,status='active',email_verified_at=NOW,password_hash='test-hash',created_at=NOW,updated_at=NOW))
        s.add(AIRuntimePolicy(id=1,version=1,policy_json=json.dumps(DEFAULT_POLICY),updated_at=NOW))
        s.add(AIProviderState(provider=PROVIDER,failures=0,open_until=0,probe_until=0))
    repo=ResumeAnalysisRepository(db);ledger=AIRepository(db)
    runtime=AIService(ledger,AISettings(),fingerprint_key='tests-only')
    service=ResumeAnalysisService(repo,runtime,fingerprint_key='tests-only',clock=lambda:NOW)
    yield db,user,other,repo,ledger,runtime,service
    db.dispose()

def request(service,user,fid='resume-analysis-ru-01',key=None):
    return AnalysisRequest(user,key or str(uuid4()),fid,service.source(fid)[2])

def reference(fid):return json.loads((ROOT/f'evals/expected/reference/{fid}.json').read_text())

class Fake:
    provider_id=PROVIDER
    def __init__(self,fid='resume-analysis-en-01',body=None):self.body=body or reference(fid);self.calls=[]
    def generate(self,call):
        self.calls.append(call)
        if isinstance(self.body,Exception):raise self.body
        return ProviderResponse(json.dumps(self.body,ensure_ascii=False),1000,300)

def enable_runtime(env,fake):
    db,user,other,repo,ledger,runtime,service=env
    v,_=ledger.read_policy();ledger.update_policy({'enabled':True,'kill_switch':False},expected_version=v,now=NOW)
    runtime.settings=AISettings(True,False,True,'test-placeholder','fixture-folder','gpt://fixture-folder/aliceai-llm/latest',NOW-86401)
    runtime.provider=fake;runtime.clock=lambda:NOW
    return service

@pytest.mark.parametrize('fid',['resume-analysis-ru-01','resume-analysis-en-01'])
def test_reference_saved_versioned_and_evidence_linked(env,fid):
    db,user,other,repo,ledger,runtime,svc=env
    result=svc.create_reference(request(svc,user,fid))
    assert result.status=='succeeded' and result.reason=='reference_not_live_ai'
    report=result.report
    assert report['origin']=='reference' and report['source_facts'] and report['version']==1
    assert all(v['decision']=='pending' and v['revision']==0 for v in report['decisions'].values())
    assert not ledger.owner_usage(user)
    assert repo.get(other,report['id']) is None
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(CareerProfile))==0
        assert s.scalar(select(func.count()).select_from(ResumeDraft))==0
    db.dispose();assert repo.get(user,report['id'])['result']==report['result']
    assert svc.create_reference(request(svc,user,fid)).report['version']==2

def test_reference_never_uses_network_even_when_runtime_open(env,monkeypatch):
    svc=enable_runtime(env,Fake('resume-analysis-ru-01'))
    def forbidden(*args,**kwargs):raise AssertionError('must not dispatch')
    monkeypatch.setattr(svc.runtime,'generate',forbidden)
    assert svc.create_reference(request(svc,env[1])).status=='succeeded'

def test_same_operation_reference_is_idempotent_and_scoped(env):
    db,user,other,repo,ledger,runtime,svc=env
    r=request(svc,user);a=svc.create_reference(r);b=svc.create_reference(r)
    assert a.report['id']==b.report['id'] and len(repo.list(user))==1
    r2=request(svc,other,key=r.idempotency_key)
    assert svc.create_reference(r2).report['id']!=a.report['id']
    conflict=request(svc,user,'resume-analysis-en-01',key=r.idempotency_key)
    assert svc.create_reference(conflict).reason=='idempotency_conflict'
    assert svc.analyze(r).reason=='idempotency_conflict'

@pytest.mark.parametrize('change',[
    {'fixture_id':'../../secrets'}, {'fixture_id':'resume-analysis-ru-99'},
    {'idempotency_key':''}, {'idempotency_key':'bad key'}, {'user_id':'not-a-user'},
    {'expected_source_hash':'0'*64},
])
def test_invalid_and_stale_input_never_stored(env,change):
    svc=env[-1];r=replace(request(svc,env[1]),**change)
    assert svc.create_reference(r).status=='manual' and not svc.history(env[1])
    assert not env[4].owner_usage(env[1])

def test_dictionary_or_uploaded_resume_is_not_an_analysis_request(env):
    svc=env[-1]
    assert svc.analyze({'resume':'secret user content'}).reason=='invalid_request'
    assert svc.create_reference({'resume':'secret user content'}).reason=='invalid_request'

@pytest.mark.parametrize('status,verified',[('pending',True),('active',False),('deleted',True)])
def test_reference_requires_active_verified_owner(env,status,verified):
    db,user,*_=env
    with db.session() as s,s.begin():
        u=s.get(User,user);u.status=status;u.email_verified_at=NOW if verified else None
    svc=env[-1]
    assert svc.create_reference(request(svc,user)).reason=='verified_account_required'

def test_review_accepted_is_not_a_profile_edit_and_history_is_immutable(env):
    db,user,other,repo,ledger,runtime,svc=env
    report=svc.create_reference(request(svc,user)).report
    args=dict(user_id=user,report_id=report['id'],recommendation_id='rec-1',decision='accepted',expected_revision=0,expected_source_hash=report['source_hash'])
    accepted=svc.decide(**args)
    assert accepted['decisions']['rec-1']=={'decision':'accepted','revision':1}
    assert len(accepted['review_events'])==1 and accepted['result']==report['result']
    assert len(svc.decide(**args)['review_events'])==1
    with pytest.raises(AnalysisError,match='stale_review'):svc.decide(**{**args,'decision':'rejected'})
    changed=svc.decide(**{**args,'decision':'rejected','expected_revision':1})
    assert len(changed['review_events'])==2 and changed['decisions']['rec-1']['revision']==2
    reset=svc.decide(**{**args,'decision':'pending','expected_revision':2})
    assert len(reset['review_events'])==3
    with db.session() as s:assert s.scalar(select(func.count()).select_from(CareerProfile))==0
    assert svc.get(user,report['id'])['result']==report['result']

@pytest.mark.parametrize('change,error',[
    ({'decision':'approve-all'},'invalid_decision'),({'expected_revision':-1},'invalid_decision'),
    ({'expected_revision':True},'invalid_decision'),({'recommendation_id':'rec-99'},'not_found'),
    ({'expected_source_hash':'f'*64},'stale_source')])
def test_invalid_reviews(env,change,error):
    db,user,other,repo,ledger,runtime,svc=env;r=svc.create_reference(request(svc,user)).report
    args=dict(user_id=user,report_id=r['id'],recommendation_id='rec-1',decision='accepted',expected_revision=0,expected_source_hash=r['source_hash'])
    with pytest.raises(AnalysisError,match=error):svc.decide(**{**args,**change})
    with pytest.raises(AnalysisError,match='not_found'):svc.decide(**{**args,'user_id':other})
    assert not svc.get(user,r['id'])['review_events']

def test_parallel_reference_save_and_review_are_serialized(env):
    db,user,other,repo,ledger,runtime,svc=env;r=request(svc,user)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:svc.create_reference(r),range(4)))
    assert all(x.report for x in results) and len({x.report['id'] for x in results})==1
    report=results[0].report
    def change(decision):
        try:return svc.decide(user_id=user,report_id=report['id'],recommendation_id='rec-1',decision=decision,expected_revision=0,expected_source_hash=report['source_hash'])
        except AnalysisError as e:return str(e)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(change,['accepted','rejected']))
    assert sum(isinstance(x,dict) for x in results)==1 and 'stale_review' in results

@pytest.mark.parametrize('fid',['resume-analysis-ru-01','resume-analysis-en-01'])
def test_provider_result_saves_once_via_existing_cost_runtime(env,fid):
    fake=Fake(fid);svc=enable_runtime(env,fake);r=request(svc,env[1],fid)
    a=svc.analyze(r);b=svc.analyze(r)
    assert a.status=='succeeded' and a.report['origin']=='provider'
    assert b.report['id']==a.report['id'] and len(fake.calls)==1
    assert len(env[4].owner_usage(env[1]))==1

def test_runtime_closed_does_not_generate(env):
    svc=env[-1];res=svc.analyze(request(svc,env[1]));assert res.status=='manual' and not res.report
    assert res.reason=='runtime_not_activated' and not env[4].owner_usage(env[1])

def test_grounding_failure_accounts_tokens_but_never_saves(env):
    body=reference('resume-analysis-en-01');body['strengths'][0]['evidence_ids']=['e99']
    fake=Fake(body=body);svc=enable_runtime(env,fake)
    res=svc.analyze(request(svc,env[1],'resume-analysis-en-01'))
    assert res.reason=='feature_validation_failure' and not svc.history(env[1])
    with env[0].session() as s:
        e=s.scalar(select(AIUsageEvent));assert e.status=='failed' and e.charged_microrub==860000 and not e.commercial_action_consumed

def test_failed_report_save_never_repeats_billable_call(env,monkeypatch):
    fake=Fake();svc=enable_runtime(env,fake);r=request(svc,env[1],'resume-analysis-en-01')
    original=svc.repository.save
    def fail(**kwargs):raise OSError('do not leak raw database details')
    monkeypatch.setattr(svc.repository,'save',fail)
    assert svc.analyze(r).reason=='storage_unavailable'
    monkeypatch.setattr(svc.repository,'save',original)
    assert svc.analyze(r).status=='manual' and len(fake.calls)==1

def test_provider_unknown_failure_keeps_reservation(env):
    fake=Fake(body=ProviderError('timeout_unknown'));svc=enable_runtime(env,fake)
    assert svc.analyze(request(svc,env[1],'resume-analysis-en-01')).status=='manual'
    assert len(fake.calls)==1 and not svc.history(env[1])
    with env[0].session() as s:assert s.scalar(select(AIUsageEvent)).cost_uncertain

@pytest.mark.parametrize('mutation',[
    'bad_id','missing_gap','positive_gap','new_number','impact','html','technical','duplicate_id','wrong_evidence','absolute_gap','summary_gap',
])
def test_fixed_fixture_validator_rejects_unsupported_output(mutation):
    fid='resume-analysis-en-01';fixture,schema=ContractRegistry().load(fid);body=reference(fid)
    if mutation=='bad_id':body['strengths'][0]['evidence_ids']=['e99']
    if mutation=='missing_gap':body['facts_not_verified']=[]
    if mutation=='positive_gap':body['strengths'][0]['evidence_ids']=['e5']
    if mutation=='new_number':body['strengths'][0]['explanation']='Ten years as a data analyst.'
    if mutation=='impact':body['strengths'][1]['explanation']='Advanced SQL increased revenue.'
    if mutation=='html':body['summary']+='<script>alert(1)</script>'
    if mutation=='technical':body['summary']+=' (e1, e2)'
    if mutation=='duplicate_id':body['strengths'][1]['evidence_ids']=['e2','e2']
    if mutation=='wrong_evidence':body['strengths'][1]['evidence_ids']=['e1']
    if mutation=='absolute_gap':body['gaps'][0]['explanation']='The candidate has no experience with Python.'
    if mutation=='summary_gap':body['summary']='The candidate has two years as a data analyst with advanced SQL and Power BI. Has extensive Python experience.'
    with pytest.raises(ContractError):validate_analysis(body,fixture,schema)

def test_reference_checksum_tamper_fails_closed(env,tmp_path):
    import shutil
    root=tmp_path/'root'
    for folder in ('prompts','schemas','services/ai'):
        shutil.copytree(ROOT/folder,root/folder)
    p=root/'prompts/analysis/reference/resume-analysis-ru-01.json';p.write_text('{}')
    svc=ResumeAnalysisService(env[3],env[5],fingerprint_key='tests-only',root=root)
    assert svc.create_reference(request(svc,env[1])).reason=='invalid_reference'

def test_private_exports_and_cascade_delete_are_owner_scoped(env):
    db,user,other,repo,ledger,runtime,svc=env
    a=svc.create_reference(request(svc,user)).report;b=svc.create_reference(request(svc,other)).report
    svc.decide(user_id=user,report_id=a['id'],recommendation_id='rec-1',decision='accepted',expected_revision=0,expected_source_hash=a['source_hash'])
    snapshot,_=PrivacyRepository(db).export_snapshot(user,expected_password_hash='test-hash')
    assert len(snapshot['resume_analyses'])==1 and snapshot['resume_analyses'][0]['id']==a['id']
    assert len(snapshot['resume_analyses'][0]['review_events'])==1
    assert 'operation_hash' not in json.dumps(snapshot['resume_analyses'])
    with pytest.raises(AnalysisError):svc.delete(other,a['id'],a['source_hash'])
    counts=PrivacyRepository(db).delete_account(user,expected_password_hash='test-hash',now=NOW)
    assert counts['resume_analysis_reports']==1 and repo.get(user,a['id']) is None and repo.get(other,b['id'])
    with db.session() as s:
        assert not s.scalars(select(ResumeAnalysisDecision).where(ResumeAnalysisDecision.report_id==a['id'])).all()
        assert not s.scalars(select(ResumeAnalysisReviewEvent).where(ResumeAnalysisReviewEvent.report_id==a['id'])).all()

def test_explicit_report_delete_removes_decisions_only_not_user(env):
    db,user,other,repo,ledger,runtime,svc=env;a=svc.create_reference(request(svc,user)).report
    svc.delete(user,a['id'],a['source_hash']);assert repo.get(user,a['id']) is None
    with db.session() as s:assert s.get(User,user)
