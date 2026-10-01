"""General Alice path with a stubbed transport and disposable SQLite only."""
from dataclasses import replace
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import copy
import json
import pytest
from sqlalchemy import select,func,delete

from domain.cover_letter import LetterError,compose
from domain.ai import ProviderError,PROVIDER
from models import User
from models.cover_letter import CoverLetterProposal,CoverLetterVersion
from models.ai import AIUsageEvent,AIBudgetBucket
from repositories.ai import AIRepository
from services.ai.service import AIService
from services.ai.settings import AISettings
from services.ai.provider import YandexAliceProvider
from services.ai.letter_runtime import LetterRuntime
from services.ai.letter_contract import build_writing_contract
from services.cover_letter_ai import CoverLetterGenerator
from services.ai.letter_admission import ClosedLetterAdmission
from tests.test_ai005_service import letters,new,save,profile_payload
from tests.test_job001_service import job_env

NOW=1789905600

class TestAdmission:
    __test__=False
    enabled=True
    def check(self,**kwargs):
        if not self.enabled:raise LetterError('generation_unavailable')
        return 'unit-test-synthetic-only'

class StubTransport:
    def __init__(self):
        self.calls=[];self.before=None;self.error=None;self.mutate=None
    def __call__(self,payload,timeout):
        self.calls.append(copy.deepcopy(payload))
        if self.before:self.before()
        if self.error:raise self.error
        data=json.loads(payload['body']['messages'][1]['content'])
        fact=data['candidate_facts'][0]
        body={'source_hash':data['source_hash'],'subject':'Application',
              'paragraphs':[
                {'kind':'opening','text':'I would like to apply for this role.',
                 'candidate_evidence':[],'vacancy_evidence':['title']},
                {'kind':'candidate_fit','text':fact['text'],
                 'candidate_evidence':[{'id':fact['id'],'quote':fact['text']}],'vacancy_evidence':[]},
                {'kind':'closing','text':'Thank you for considering my application.',
                 'candidate_evidence':[],'vacancy_evidence':[]},
              ],'caveats':[]}
        reply={'ok':True,'envelope':{'choices':[{'message':{'content':json.dumps(body)},'finish_reason':'stop'}],
                                   'usage':{'prompt_tokens':1000,'completion_tokens':300}}}
        if self.mutate:self.mutate(reply)
        return reply

@pytest.fixture
def live(letters):
    e=letters;record=save(e,new(e))
    ledger=AIRepository(e.db);version,_=ledger.read_policy()
    ledger.update_policy({'enabled':True,'kill_switch':False},expected_version=version,now=NOW)
    settings=AISettings(True,False,True,'unit-test-key','fixture-folder',
        'gpt://fixture-folder/aliceai-llm/latest',NOW-86401)
    transport=StubTransport();provider=YandexAliceProvider(settings,transport=transport)
    ai=AIService(ledger,settings,fingerprint_key='synthetic-key',provider=provider,clock=lambda:NOW)
    runtime=LetterRuntime(ai,clock=lambda:NOW)
    gate=TestAdmission();clock=[NOW]
    generator=CoverLetterGenerator(e.svc.repository,runtime,signing_key='test-preview-key',
        admission=gate,clock=lambda:clock[0])
    preview=generator.preview(e.owner,record['id'],record['revision'],'en','short','professional',['profile.summary'])
    return SimpleNamespace(e=e,record=record,ledger=ledger,runtime=runtime,gate=gate,clock=clock,
        transport=transport,generator=generator,preview=preview)


def run(x,**kwargs):
    return x.generator.generate(x.e.owner,x.record['id'],x.preview['review_token'],confirmed=kwargs.get('confirmed',True))


def events(x):
    with x.e.db.session() as s:
        return list(s.scalars(select(AIUsageEvent)))


def test_provider_path_saves_pending_proposal_and_accounting_atomically(live,monkeypatch):
    x=live
    monkeypatch.setattr('domain.cover_letter.compose',lambda *a,**k:(_ for _ in ()).throw(AssertionError('not a template')))
    result=run(x);assert result['status']=='proposal'
    p=result['proposal'];assert p['origin']=='alice_draft'
    assert 'Built REST API tests' in p['content']['body']
    current=x.e.svc.get(x.e.owner,x.record['id'])
    assert current['content']==x.record['content'] and current['last_version']==1
    assert len(current['proposals'])==1
    event=events(x)[0]
    assert event.prompt_version=='cover-letter-draft-v1' and event.status=='succeeded'
    assert event.charged_microrub==860000 and event.attempts==1
    assert event.fixture_id=='general-letter-draft'
    assert not event.commercial_action_consumed
    payload=x.transport.calls[0]
    assert payload['headers']['x-data-logging-enabled']=='false'
    assert payload['body']['model'].endswith('/aliceai-llm/latest')
    assert payload['body']['response_format']['type']=='json_schema'
    sent=json.dumps(payload['body'])
    for private in (x.e.owner,x.record['id'],x.e.saved_id,'private@example.test','Private note'):
        assert private not in sent


def test_duplicate_pending_and_deleted_proposal_never_redispatch(live):
    x=live;first=run(x);again=run(x)
    assert again['proposal']['id']==first['proposal']['id'] and len(x.transport.calls)==1
    x.e.svc.reject(x.e.owner,x.record['id'],first['proposal']['id'],x.record['revision'],confirmed=True)
    replay=run(x)
    assert replay['status']=='already_processed' and len(x.transport.calls)==1
    assert len(events(x))==1


@pytest.mark.parametrize('edit',[False,True])
def test_acceptance_creates_reviewed_version_with_explicit_ai_origin(live,edit):
    x=live;p=run(x)['proposal'];c=p['content'].copy()
    if edit:c['body']+='\nA human edit.'
    saved=x.e.svc.save(x.e.owner,x.record['id'],x.record['revision'],**c,confirmed=True,proposal_id=p['id'])
    v=x.e.svc.version(x.e.owner,x.record['id'],saved['last_version'])
    assert v['origin']==('user_edited_alice_draft' if edit else 'alice_draft')
    assert v['evidence']['semantic_grounding']=='human_review_required'
    assert not x.e.svc.get(x.e.owner,x.record['id'])['proposals']
    assert c['body'] in x.e.svc.export_text(x.e.owner,x.record['id'],saved['last_version']).decode('utf-8-sig')
    assert run(x)['status']=='manual' and len(x.transport.calls)==1


def test_preview_confirmation_binding_and_expiry(live):
    x=live
    with pytest.raises(LetterError,match='confirmation_required'):run(x,confirmed=False)
    for token in (None,'bad',x.preview['review_token']+'x'):
        with pytest.raises(LetterError):x.generator.generate(x.e.owner,x.record['id'],token,confirmed=True)
    x.clock[0]+=600
    with pytest.raises(LetterError,match='invalid_preview'):run(x)
    assert not x.transport.calls and not events(x)


def test_foreign_document_and_replayed_ticket_are_denied(live):
    x=live
    with pytest.raises(LetterError,match='not_found'):
        x.generator.generate(x.e.other,x.record['id'],x.preview['review_token'],confirmed=True)
    second=new(x.e)
    with pytest.raises(LetterError,match='invalid_preview'):
        x.generator.generate(x.e.owner,second['id'],x.preview['review_token'],confirmed=True)
    assert not x.transport.calls


def test_all_environment_flags_cannot_open_default_legal_gate(live):
    x=live;g=CoverLetterGenerator(x.e.svc.repository,x.runtime,signing_key='test')
    with pytest.raises(LetterError,match='generation_unavailable'):
        g.generate(x.e.owner,x.record['id'],x.preview['review_token'],confirmed=True)
    with pytest.raises(LetterError,match='generation_unavailable'):
        g.preview(x.e.owner,x.record['id'],2,'en','short','professional',['profile.summary'])
    assert not x.transport.calls and not events(x)


@pytest.mark.parametrize('change',['source','letter','gate'])
def test_changes_before_dispatch_do_not_reserve_or_call(live,change):
    x=live
    if change=='source':
        value=profile_payload();value['summary']='A different confirmed fact.'
        x.e.profile.save(user_id=x.e.owner,payload=value,expected_version=1)
    if change=='letter':save(x.e,x.record,body='A newer manual letter.')
    if change=='gate':x.gate.enabled=False
    if change=='gate':
        with pytest.raises(LetterError):run(x)
    else:assert run(x)['status']=='manual'
    assert not x.transport.calls and not events(x)


def test_impossible_selected_fact_is_rejected_during_preview_without_provider_call(live):
    x=live;value=profile_payload();value['summary']='x'*1801
    x.e.profile.save(user_id=x.e.owner,payload=value,expected_version=1)
    record=save(x.e,new(x.e))
    with pytest.raises(LetterError,match='^input_limit$'):
        x.generator.preview(x.e.owner,record['id'],record['revision'],
                            'en','full','professional',['profile.summary'])
    assert not x.transport.calls and not events(x)


def test_eight_fact_full_selection_builds_preview_without_provider_usage(live):
    x=live;value=profile_payload()
    value['skills']=[{'name':f'Safe skill {index}'} for index in range(8)]
    x.e.profile.save(user_id=x.e.owner,payload=value,expected_version=1)
    record=save(x.e,new(x.e,length='full'))
    fact_ids=[f'profile.skills.{index}.name' for index in range(8)]
    preview=x.generator.preview(x.e.owner,record['id'],record['revision'],
                                'en','full','professional',fact_ids)
    assert preview['review_token']
    assert not x.transport.calls and not events(x)


@pytest.mark.parametrize('unsafe_fact',[
    '<b>Built APIs</b>',
    'I have long admired this company.',
    'I have long\tadmired this company.',
    'I have long\nadmired this company.',
    'I have long\u00a0admired this company.',
    'I have long    admired this company.',
    'Я давно\tслежу за компанией.',
    'Я давно\nслежу за компанией.',
    'Я давно\u00a0слежу за компанией.',
    'Я давно    слежу за компанией.',
])
def test_unsafe_verbatim_fact_is_rejected_during_preview_without_usage(live,unsafe_fact):
    x=live;value=profile_payload();value['summary']=unsafe_fact
    x.e.profile.save(user_id=x.e.owner,payload=value,expected_version=1)
    record=save(x.e,new(x.e))
    with pytest.raises(LetterError,match='^invalid_source$'):
        x.generator.preview(x.e.owner,record['id'],record['revision'],
                            'en','short','professional',['profile.summary'])
    assert not x.transport.calls and not events(x)


@pytest.mark.parametrize('change',['source','letter','delete','gate','kill'])
def test_changes_during_provider_suppress_delivery_without_success_charge(live,change):
    x=live
    def mutate():
        # This write during the transport call also proves no owner transaction
        # is held across the network boundary.
        if change=='source':
            v=profile_payload();v['summary']='Changed while provider was running.'
            x.e.profile.save(user_id=x.e.owner,payload=v,expected_version=1)
        if change=='letter':save(x.e,x.record,body='Human version wins.')
        if change=='delete':x.e.svc.delete(x.e.owner,x.record['id'],2,confirmed=True)
        if change=='gate':x.gate.enabled=False
        if change=='kill':
            version,_=x.ledger.read_policy()
            x.ledger.update_policy({'kill_switch':True},expected_version=version,now=NOW)
    x.transport.before=mutate
    result=run(x)
    assert result['status']=='manual' and result['reason']=='result_not_delivered'
    event=events(x)[0]
    assert event.status=='failed' and event.charged_microrub==860000
    assert not event.commercial_action_consumed
    with x.e.db.session() as s:
        assert s.scalar(select(func.count()).select_from(CoverLetterProposal))==0


@pytest.mark.parametrize('error,uncertain',[
    (ProviderError('timeout_unknown'),True),
    (ProviderError('upstream_error',retryable=True),True),
    (ProviderError('permission_denied',unknown=False),False),
    (RuntimeError('secret error must not escape'),True)])
def test_provider_failures_conservatively_accounted_without_automatic_retry(live,error,uncertain):
    x=live;x.transport.error=error
    result=run(x)
    assert result['status']=='manual' and 'secret' not in json.dumps(result)
    event=events(x)[0]
    assert event.cost_uncertain==uncertain and event.status==('unknown' if uncertain else 'failed')
    assert bool(event.charged_microrub)==uncertain
    replay=run(x)
    assert replay['status']=='already_processed' and len(x.transport.calls)==1


@pytest.mark.parametrize('mutation',['bad_json','refusal','missing_usage','input_overrun'])
def test_response_outcomes_cost_and_delivery(live,mutation):
    x=live
    def change(reply):
        envelope=reply['envelope']
        if mutation=='bad_json':envelope['choices'][0]['message']['content']='not-json'
        if mutation=='refusal':envelope['choices'][0]['message']['refusal']='refused'
        if mutation=='missing_usage':envelope.pop('usage')
        if mutation=='input_overrun':envelope['usage']['prompt_tokens']=8001
    x.transport.mutate=change
    result=run(x);event=events(x)[0]
    if mutation=='missing_usage':
        assert result['status']=='proposal' and event.cost_uncertain
    else:
        assert result['status']=='manual' and event.status=='failed'
    if mutation=='bad_json':
        assert result['reason']=='feature_validation_failure'
        assert event.reason=='validation_schema'
    if mutation=='input_overrun':assert x.ledger.read_policy()[1]['kill_switch']
    assert len(x.transport.calls)==1


def test_unallowlisted_validator_error_stays_generic(live,monkeypatch):
    x=live
    monkeypatch.setattr('services.ai.letter_runtime.validate_writing',
                        lambda *_: (_ for _ in ()).throw(LetterError('private response detail')))
    result=run(x);event=events(x)[0]
    assert result['reason']=='feature_validation_failure'
    assert event.reason=='feature_validation_failure'
    assert 'private response detail' not in json.dumps(result)


def test_candidate_claim_grounding_reason_is_internal_and_public_result_is_generic(live):
    x=live
    def invent(reply):
        body=json.loads(reply['envelope']['choices'][0]['message']['content'])
        body['paragraphs'][1]['text']='I design Kubernetes clusters.'
        reply['envelope']['choices'][0]['message']['content']=json.dumps(body)
    x.transport.mutate=invent
    result=run(x);event=events(x)[0]
    assert result['reason']=='feature_validation_failure'
    assert event.reason=='validation_candidate_claim_grounding'
    assert 'Kubernetes' not in json.dumps(result)


def test_insertion_failure_keeps_reservation_and_no_orphan_proposal(live,monkeypatch):
    x=live
    def fail(*args,**kwargs):raise RuntimeError('private storage failure')
    monkeypatch.setattr(x.e.svc.repository,'insert_ai_proposal',fail)
    result=run(x)
    assert result['status']=='manual' and result['reason']=='ledger_unavailable'
    event=events(x)[0];assert event.status=='reserved' and event.cost_uncertain
    x.ledger.recover(now=NOW+200)
    assert events(x)[0].status=='unknown'
    assert run(x)['status']=='already_processed' and len(x.transport.calls)==1


def test_no_environment_or_database_permission_no_calls(live):
    x=live;x.runtime.settings=replace(x.runtime.settings,enabled=False)
    assert run(x)['status']=='manual' and not events(x) and not x.transport.calls


def test_parallel_same_preview_dispatches_once(live):
    x=live
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:run(x),range(2)))
    assert len(x.transport.calls)==1 and len(events(x))==1
    assert any(r['status']=='proposal' for r in results)
