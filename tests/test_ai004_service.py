"""Persistence, isolation, idempotency, privacy and closed provider integration."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import uuid4
import json
import shutil
import pytest
from sqlalchemy import select, func, delete
from database import create_database
from models import Base, User, CareerProfile, ResumeDraft, Vacancy
from models.ai import AIUsageEvent
from models.vacancy_match import VacancyMatchReport, VacancyMatchSeries
from repositories.vacancy_match import VacancyMatchRepository
from repositories.privacy import PrivacyRepository
from repositories.ai import AIRepository
from services.vacancy_match import VacancyMatchService, ROOT
from services.ai.service import AIService
from services.ai.settings import AISettings
from domain.vacancy_match import MatchError, MatchRequest
from services.ai.registry import ContractError
from tests.test_ai001_runtime import Fake, enable, service as live_service

NOW = 1789560000

@pytest.fixture
def env(tmp_path):
    db = create_database(f'sqlite:///{tmp_path}/match.db')
    Base.metadata.create_all(db.engine)
    owner, other = str(uuid4()), str(uuid4())
    with db.session() as session, session.begin():
        for uid in (owner,other):
            session.add(User(id=uid, status='active', email_verified_at=NOW, password_hash='test-only',created_at=NOW,updated_at=NOW))
    runtime = AIService(AIRepository(db), AISettings(), fingerprint_key='test-only', clock=lambda:NOW)
    svc = VacancyMatchService(VacancyMatchRepository(db), runtime, fingerprint_key='test-only', clock=lambda:NOW)
    yield db, owner, other, svc
    db.dispose()


def req(env, language='ru', owner=None, key=None):
    fid='vacancy-match-'+language+'-01'
    return MatchRequest(owner or env[1], fid, env[-1].source(fid)[2], key or str(uuid4()))


def test_reference_versioning_hashes_reconnect_and_no_core_mutation(env):
    db, owner, _, svc = env
    first=svc.create_reference(req(env));second=svc.create_reference(req(env))
    assert first['version'] == 1 and second['version'] == 2
    assert first['result_hash'] == second['result_hash']
    assert len(first['source_hash']) == len(first['candidate_hash']) == len(first['vacancy_hash']) == 64
    assert len({first['source_hash'],first['candidate_hash'],first['vacancy_hash']}) == 3
    db.dispose()
    assert svc.get(owner,first['id'])['result'] == first['result']
    assert not svc.get(owner,first['id'])['stale_source']
    with db.session() as session:
        for model in (AIUsageEvent,CareerProfile,ResumeDraft,Vacancy):
            assert session.scalar(select(func.count()).select_from(model)) == 0
    assert 'operation_hash' not in json.dumps(svc.history(owner))


def test_duplicate_operation_is_a_noop_and_cross_source_reuse_is_conflict(env):
    request=req(env);first=env[-1].create_reference(request)
    assert env[-1].create_reference(request) == first
    with pytest.raises(MatchError,match='idempotency_conflict'):
        env[-1].create_reference(req(env,language='en',key=request.operation_key))
    with pytest.raises(MatchError,match='stale_source'):
        env[-1].create_reference(replace(request, source_hash='0'*64))
    assert len(env[-1].history(env[1])) == 1


def test_parallel_duplicate_creates_one_report_and_independent_requests_are_serialized(env):
    request=req(env)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:env[-1].create_reference(request),range(4)))
    assert len({r['id'] for r in results}) == 1
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda _:env[-1].create_reference(req(env)),range(3)))
    assert sorted(r['version'] for r in results) == [2,3,4]


def test_cross_owner_read_delete_and_privacy_export(env):
    db,owner,other,svc=env
    first=svc.create_reference(req(env));second=svc.create_reference(req(env,owner=other))
    with pytest.raises(MatchError,match='not_found'):svc.get(other,first['id'])
    with pytest.raises(MatchError,match='not_found'):svc.delete(other,first['id'],first['result_hash'])
    assert [r['id'] for r in svc.history(other)] == [second['id']]
    privacy=PrivacyRepository(db)
    snapshot,_=privacy.export_snapshot(owner, expected_password_hash='test-only')
    assert [r['id'] for r in snapshot['vacancy_matches']] == [first['id']]
    assert snapshot['vacancy_match_series'] == [{'fixture_id':first['fixture_id'],'last_version':1}]
    assert 'operation_hash' not in json.dumps(snapshot['vacancy_matches'])
    counts=privacy.delete_account(owner,expected_password_hash='test-only',now=NOW)
    assert counts['vacancy_match_reports'] == counts['vacancy_match_series'] == 1
    assert svc.get(other,second['id'])['version'] == 1
    with db.session() as session:
        assert session.scalar(select(func.count()).select_from(VacancyMatchSeries).where(VacancyMatchSeries.user_id==owner)) == 0
        assert session.scalar(select(func.count()).select_from(VacancyMatchReport).where(VacancyMatchReport.user_id==owner)) == 0


def test_delete_never_reuses_versions_and_stale_confirmation_is_rejected(env):
    svc=env[-1];first=svc.create_reference(req(env));second=svc.create_reference(req(env))
    with pytest.raises(MatchError,match='stale_report'):svc.delete(env[1],second['id'],'0'*64)
    svc.delete(env[1],second['id'],second['result_hash'])
    with pytest.raises(MatchError,match='not_found'):svc.get(env[1],second['id'])
    third=svc.create_reference(req(env))
    assert third['version'] == 3 and svc.get(env[1],first['id'])['version'] == 1


@pytest.mark.parametrize('changes', [{'user_id':'not-a-uuid'},{'fixture_id':'real-resume'}, {'fixture_id':['vacancy-match-ru-01']},
    {'source_hash':None},{'operation_key':'x'},{'operation_key':None}])
def test_rejects_untrusted_requests(env,changes):
    with pytest.raises(MatchError):env[-1].create_reference(replace(req(env),**changes))
    assert not env[-1].history(env[1])


def test_unverified_or_deleted_account_is_rejected(env):
    with env[0].session() as session,session.begin():session.get(User,env[1]).email_verified_at=None
    with pytest.raises(MatchError,match='verified_account_required'):env[-1].create_reference(req(env))


def test_reference_cannot_dispatch_provider_even_when_method_is_available(env,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Reference invoked provider')
    monkeypatch.setattr(env[-1].runtime,'generate',forbidden)
    assert env[-1].create_reference(req(env))['origin'] == 'reference'


def test_public_default_runtime_does_not_create_ledger_entry(env):
    with pytest.raises(MatchError,match='provider_result_unavailable'):env[-1].analyze(req(env))
    with env[0].session() as session:assert session.scalar(select(func.count()).select_from(AIUsageEvent)) == 0


def test_history_limit_is_enforced_but_retry_of_saved_request_still_works(env,monkeypatch):
    import repositories.vacancy_match as module
    monkeypatch.setattr(module,'MAX_REPORTS_PER_OWNER',1)
    request=req(env);first=env[-1].create_reference(request)
    with pytest.raises(MatchError,match='history_limit'):env[-1].create_reference(req(env))
    assert env[-1].create_reference(request) == first


def test_reference_checksum_tamper_fails_and_preserves_history(env,tmp_path):
    root=tmp_path/'copy'
    for folder in ('services/ai','prompts/ai','schemas/ai','prompts/matching'):
        shutil.copytree(ROOT/folder,root/folder,dirs_exist_ok=True)
    svc=VacancyMatchService(env[-1].repository,env[-1].runtime,fingerprint_key='test-only',root=root)
    path=root/'prompts/matching/reference/vacancy-match-ru-01.json'
    path.write_text('{}')
    with pytest.raises(ContractError):svc.create_reference(req(env))
    assert not svc.history(env[1])


def test_corrupt_saved_result_is_not_presented_as_valid(env):
    report=env[-1].create_reference(req(env))
    with env[0].session() as session,session.begin():
        row=session.get(VacancyMatchReport,report['id']);value=json.loads(row.result_json)
        value['summary']['score_percent']=100;row.result_json=json.dumps(value)
    with pytest.raises(MatchError,match='invalid_saved_report'):env[-1].get(env[1],report['id'])


def test_changed_source_marks_history_without_rewriting_it(env,monkeypatch):
    report=env[-1].create_reference(req(env));original=env[-1].source
    monkeypatch.setattr(env[-1],'source',lambda fid:(*original(fid)[:2],'f'*64))
    read=env[-1].get(env[1],report['id'])
    assert read['stale_source'] and read['result']==report['result']


def make_provider(env, fake):
    from models.ai import AIRuntimePolicy, AIProviderState
    from services.ai.policy import DEFAULT_POLICY
    from domain.ai import PROVIDER
    with env[0].session() as session,session.begin():
        session.add(AIRuntimePolicy(id=1,version=1,policy_json=json.dumps(DEFAULT_POLICY),updated_at=NOW))
        session.add(AIProviderState(provider=PROVIDER,failures=0,open_until=0,probe_until=0))
    repo=AIRepository(env[0]);enable(repo)
    # AIService performs its normal admission, usage and feature-validator path.
    env[-1].runtime=live_service(repo,fake)
    return repo


def test_internal_provider_uses_ledger_and_saves_only_canonical_result(env):
    fake=Fake('vacancy-match-ru-01');make_provider(env,fake)
    request=req(env);first=env[-1].analyze(request)
    assert first['origin']=='provider' and first['result']['summary']['score_percent']==67
    assert env[-1].analyze(request)==first and len(fake.calls)==1
    assert 'matched_requirements' not in first['result']
    with env[0].session() as session:
        row=session.scalar(select(AIUsageEvent));assert row.status=='succeeded' and row.charged_microrub>0


def test_bad_classification_rejected_before_successful_settlement(env):
    fake=Fake('vacancy-match-ru-01');body=json.loads(fake.body)
    body['matched_requirements'].append(body['gaps'].pop(0));fake.body=json.dumps(body)
    make_provider(env,fake)
    with pytest.raises(MatchError,match='provider_result_unavailable'):env[-1].analyze(req(env))
    with env[0].session() as session:
        row=session.scalar(select(AIUsageEvent));assert row.status!='succeeded'
        assert row.reason=='feature_validation_failure'
    assert not env[-1].history(env[1]) and len(fake.calls)==1


def test_storage_failure_after_paid_settlement_does_not_make_second_call(env,monkeypatch):
    fake=Fake('vacancy-match-ru-01');make_provider(env,fake);request=req(env)
    save=env[-1].repository.save
    def fail(**kwargs):raise RuntimeError('simulated storage failure')
    monkeypatch.setattr(env[-1].repository,'save',fail)
    with pytest.raises(RuntimeError):env[-1].analyze(request)
    monkeypatch.setattr(env[-1].repository,'save',save)
    with pytest.raises(MatchError,match='provider_result_unavailable'):env[-1].analyze(request)
    assert len(fake.calls)==1 and not env[-1].history(env[1])


@pytest.mark.parametrize('field',['result_json','source_json'])
def test_saved_integrity_is_checked_in_history_and_duplicate_replay(env,field):
    svc=env[-1];request=req(env);first=svc.create_reference(request)
    with env[0].session() as session,session.begin():
        row=session.get(VacancyMatchReport,first['id'])
        data=json.loads(getattr(row,field))
        if field=='result_json':data['summary']['score_percent']=100
        else:data[0]['text']='unexpected source mutation'
        setattr(row,field,json.dumps(data))
    with pytest.raises(MatchError,match='invalid_saved_report'):svc.history(env[1])
    with pytest.raises(MatchError,match='invalid_saved_report'):svc.create_reference(request)
    with pytest.raises(MatchError,match='invalid_saved_report'):svc.get(env[1],first['id'])
