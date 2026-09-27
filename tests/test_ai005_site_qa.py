"""Browser-route tests execute production services with mock HTTP only."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
import json

import pytest
from sqlalchemy import select, func
from werkzeug.datastructures import MultiDict

from domain.ai import REAL_DATA_SUPPORTED
from domain.cover_letter import LetterError, digest, canonical
from models import User, CareerProfile, CareerProfileVersion
from models.cover_letter import CoverLetter, CoverLetterProposal, CoverLetterVersion
from models.ai import AIUsageEvent, AIBudgetBucket
from routes.letter_site_qa import BASE, create_letter_site_qa_blueprint
from services.ai.letter_admission import synthetic_cases
from services.legal_policy import CURRENT_AI_CONSENT_POLICY
from tests.site_qa_support import build_case, field, prepare_http, preview_http, NOW


@pytest.fixture
def qa_case(tmp_path):
    case = build_case(tmp_path)
    try:
        yield case
    finally:
        case.db.dispose()


def usage(x):
    with x.db.session() as s:
        return list(s.scalars(select(AIUsageEvent)))


@pytest.mark.parametrize('language,length,tone', [('ru','short','professional'), ('ru','full','professional'),
    ('ru','short','friendly'), ('en','short','professional'), ('en','full','professional'), ('en','short','friendly')])
def test_http_matrix_real_adapter_validation_and_no_confirmation_checkbox(qa_case, language, length, tone):
    x = qa_case
    path, csrf, data = prepare_http(x, language, length, tone)
    assert not x.transport.calls and not usage(x)
    assert x.client.post(BASE + '/prepare', data=data).location == path
    token, preview = preview_http(x, path, csrf)
    assert 'type="checkbox"' not in preview.get_data(as_text=True)
    again, _ = preview_http(x, path, csrf)
    assert again == token
    sent = {'csrf_token': csrf, 'review_token': token}
    assert x.client.post(path + '/generate', data=sent).status_code == 303
    assert x.client.post(path + '/generate', data=sent).status_code == 303
    assert len(x.transport.calls) == 1
    payload = json.loads(x.transport.calls[0]['body']['messages'][1]['content'])
    assert payload['candidate_facts'] == synthetic_cases()[language]['candidate_facts']
    assert payload['vacancy'] == synthetic_cases()[language]['vacancy']
    assert payload['preferences'] == {'language': language, 'length': length, 'tone': tone}
    assert x.transport.calls[0]['headers']['x-data-logging-enabled'] == 'false'
    assert usage(x)[0].attempts == 1 and usage(x)[0].status == 'succeeded'
    uid, _, record = x.qa.record(x.admin, path.rsplit('/', 1)[1])
    assert not record['last_version'] and len(record['proposals']) == 1
    assert x.client.get(path + '/versions/1/export.txt').status_code == 404
    for _ in range(3):
        assert x.client.get(path).status_code == 200
    assert len(x.transport.calls) == 1
    for private in (x.admin, uid, record['id'], record['saved_vacancy_id'], 'admin@example.test'):
        assert private not in json.dumps(x.transport.calls[0]['body'])


def test_edit_accept_manual_version_compare_and_exact_txt(qa_case):
    x = qa_case
    path, csrf, _ = prepare_http(x)
    token, _ = preview_http(x, path, csrf)
    assert x.client.post(path + '/generate', data={'csrf_token': csrf, 'review_token': token}).status_code == 303
    lid = path.rsplit('/',1)[1]
    uid, _, record = x.qa.record(x.admin, lid)
    p = record['proposals'][0]
    body = p['content']['body'] + '\nHuman correction for the synthetic case.'
    data = {'csrf_token': csrf, 'proposal_id': p['id'], 'expected_revision': '1', 'confirm': '1',
            'subject': p['content']['subject'], 'body': body}
    assert x.client.post(path + '/save', data={**data, 'confirm':'0'}).status_code == 400
    assert x.client.post(path + '/save', data=data).status_code == 303
    version = x.qa.version(x.admin, lid, 1)
    assert version['origin'] == 'user_edited_alice_draft'
    exported = x.client.get(path + '/versions/1/export.txt')
    assert exported.status_code == 200 and exported.data.decode('utf-8-sig') == data['subject'] + '\n\n' + body + '\n'
    assert x.client.get(path + '/versions/1').status_code == 200
    data.update(proposal_id='', expected_revision='2', body=body + '\nSecond manual version.')
    assert x.client.post(path + '/save', data=data).status_code == 303
    assert x.qa.version(x.admin, lid, 2)['content']['body'] == data['body']
    assert x.client.get(path + '/compare?left=1&right=2').status_code == 200
    stale = x.client.post(path + '/save', data={**data, 'body':'<script>unsaved</script>'})
    assert stale.status_code == 409 and '&lt;script&gt;unsaved&lt;/script&gt;' in stale.get_data(as_text=True)
    assert x.client.post(path + '/generate', data={'csrf_token':csrf,'review_token':token}).status_code == 409
    assert len(x.transport.calls) == 1


def test_rejection_does_not_save_or_resurrect_proposal(qa_case):
    x = qa_case
    path, csrf, _ = prepare_http(x)
    token, _ = preview_http(x, path, csrf)
    data = {'csrf_token':csrf, 'review_token':token}
    assert x.client.post(path+'/generate', data=data).status_code == 303
    lid = path.rsplit('/',1)[1]
    _, _, record = x.qa.record(x.admin,lid)
    pid = record['proposals'][0]['id']
    assert x.client.post(path+'/proposals/'+pid+'/reject', data={'csrf_token':csrf,'expected_revision':'1'}).status_code == 303
    assert x.client.post(path+'/generate',data=data).status_code == 409
    next_token, _ = preview_http(x,path,csrf)
    assert next_token == token
    assert x.client.post(path+'/generate',data={'csrf_token':csrf,'review_token':next_token}).status_code == 409
    _, _, record = x.qa.record(x.admin,lid)
    assert not record['proposals'] and not record['last_version'] and record['content']['body'] == ''
    assert len(x.transport.calls) == 1


@pytest.mark.parametrize('failure',['timeout','upstream','envelope','model','unsupported'])
def test_failure_no_retry_no_proposal_and_conservative_ledger(qa_case,failure):
    x = qa_case
    x.transport.failure = failure
    path,csrf,_ = prepare_http(x)
    token,_ = preview_http(x,path,csrf)
    data = {'csrf_token':csrf,'review_token':token}
    response = x.client.post(path+'/generate',data=data)
    assert response.status_code == 503
    assert x.client.post(path+'/generate',data=data).status_code == 409
    assert len(x.transport.calls) == 1
    with x.db.session() as s:
        assert s.scalar(select(func.count()).select_from(CoverLetterProposal)) == 0
    event = usage(x)[0]
    assert event.status == ('unknown' if failure in ('timeout','upstream','envelope') else 'failed')
    assert event.charged_microrub > 0 and not event.commercial_action_consumed
    raw = response.get_data(as_text=True)
    assert 'secret sentinel' not in raw and 'unit-test-api-key' not in raw


def test_creation_binding_csrf_strict_forms_and_no_request_level_switches(qa_case):
    x = qa_case
    path,csrf,data = prepare_http(x)
    assert x.client.post(BASE+'/prepare', data={**data,'language':'ru'}).status_code == 409
    assert x.client.post(BASE+'/prepare', data={**data,'intention':data['intention']+'x'}).status_code == 409
    assert x.client.post(path+'/preview',data={}).status_code == 400
    token,_ = preview_http(x,path,csrf)
    valid = {'csrf_token':csrf,'review_token':token}
    for extra in ({'user_id':x.admin},{'fixture':'custom'},{'profile':'private'}, {'confirm':'1'}, {'live_enabled':'1'}):
        assert x.client.post(path+'/generate',data={**valid,**extra}).status_code == 400
    duplicate = MultiDict(valid); duplicate.add('review_token',token)
    assert x.client.post(path+'/generate',data=duplicate).status_code == 400
    assert x.client.post(path+'/generate',json=valid,headers={'X-CSRFToken':csrf}).status_code == 400
    assert x.client.post(path+'/generate?language=ru',data=valid).status_code == 400
    assert not x.transport.calls and not usage(x)


def test_admin_owner_isolation_private_headers_and_persisted_revocation(qa_case):
    x=qa_case
    path,csrf,_=prepare_http(x)
    x.identity.user=SimpleNamespace(id=x.other,email='other-admin@example.test',status='active',email_verified_at=NOW)
    for suffix in ('','/versions/1','/versions/1/export.txt','/compare?left=1&right=2'):
        reply=x.client.get(path+suffix)
        assert reply.status_code==404 and 'no-store' in reply.headers['Cache-Control']
    assert x.client.post(path+'/preview',data={'csrf_token':csrf}).status_code==404
    x.identity.user=SimpleNamespace(id=x.ordinary,email='ordinary@example.test',status='active',email_verified_at=NOW)
    assert x.client.get(BASE).status_code==404
    x.identity.user=None
    assert x.client.get(BASE).status_code==404
    x.identity.user=SimpleNamespace(id=x.admin,email='admin@example.test',status='active',email_verified_at=NOW)
    with x.db.session() as s,s.begin():s.get(User,x.admin).status='disabled'
    assert x.client.get(BASE).status_code==404
    assert not x.transport.calls


def test_real_profile_is_never_a_source_and_internal_owners_cannot_login(qa_case):
    x=qa_case
    from services.profile import CareerProfileService
    CareerProfileService(x.storage.profiles).save(user_id=x.admin,payload={'summary':'PRIVATE PROFILE MUST NOT BE SENT'},expected_version=0)
    path,csrf,_=prepare_http(x)
    token,page=preview_http(x,path,csrf)
    assert 'PRIVATE PROFILE' not in page.get_data(as_text=True)
    assert x.client.post(path+'/generate',data={'csrf_token':csrf,'review_token':token}).status_code==303
    assert 'PRIVATE PROFILE' not in json.dumps(x.transport.calls)
    uid,_,_=x.qa.record(x.admin,path.rsplit('/',1)[1])
    with x.db.session() as s:
        user=s.get(User,uid)
        assert user.email is None and user.normalized_email is None and user.password_hash is None
        assert not user.auth_sessions and not user.auth_tokens and not user.oauth_connections
    assert REAL_DATA_SUPPORTED is False and CURRENT_AI_CONSENT_POLICY.release_state=='DRAFT'


def test_source_tampering_and_changed_revision_block_dispatch(qa_case):
    x=qa_case
    path,csrf,_=prepare_http(x)
    token,_=preview_http(x,path,csrf)
    uid,_,_=x.qa.record(x.admin,path.rsplit('/',1)[1])
    with x.db.session() as s,s.begin():
        profile=s.scalar(select(CareerProfile).where(CareerProfile.user_id==uid))
        version=s.scalar(select(CareerProfileVersion).where(CareerProfileVersion.profile_id==profile.id))
        payload={'summary':'Arbitrary replacement not in the fixture'}
        profile.content_hash=digest(payload);version.content_hash=digest(payload);version.snapshot_json=canonical(payload)
    assert x.client.post(path+'/preview',data={'csrf_token':csrf}).status_code==409
    assert x.client.post(path+'/generate',data={'csrf_token':csrf,'review_token':token}).status_code in (409,503)
    assert not x.transport.calls and not usage(x)


def test_revoked_actor_during_provider_blocks_atomic_delivery(qa_case):
    x=qa_case
    path,csrf,_=prepare_http(x);token,_=preview_http(x,path,csrf)
    def revoke():
        with x.db.session() as s,s.begin():s.get(User,x.admin).status='disabled'
    x.transport.before=revoke
    assert x.client.post(path+'/generate',data={'csrf_token':csrf,'review_token':token}).status_code==503
    assert usage(x)[0].status=='failed' and usage(x)[0].charged_microrub>0
    with x.db.session() as s:assert s.scalar(select(func.count()).select_from(CoverLetterProposal))==0


def test_expired_preview_cannot_be_refreshed_or_replayed(qa_case):
    x=qa_case
    path,csrf,_=prepare_http(x);token,_=preview_http(x,path,csrf)
    x.clock[0]+=601
    assert x.client.post(path+'/preview',data={'csrf_token':csrf}).status_code==409
    assert x.client.post(path+'/generate',data={'csrf_token':csrf,'review_token':token}).status_code==409
    assert not x.transport.calls


def test_concurrent_preparation_dispatch_and_restart_keep_one_operation(qa_case):
    x=qa_case
    intention=x.qa.new_intention(x.admin)
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids=list(pool.map(lambda _:x.qa.prepare(x.admin,intention,'en','short','professional'),range(2)))
    assert ids[0]==ids[1]
    lid=ids[0];token=x.qa.preview(x.admin,lid)['review_token']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:x.qa.generate(x.admin,lid,token),range(2)))
    assert any(r['status']=='proposal' for r in results) and len(x.transport.calls)==1
    from services.letter_site_qa import LetterSiteQA
    restarted=LetterSiteQA(x.storage,x.settings,enabled=True,live_enabled=True,provider=x.qa.ai.provider,clock=lambda:x.clock[0])
    assert restarted.preview(x.admin,lid)['review_token']==token
    assert restarted.generate(x.admin,lid,token)['status']=='proposal'
    assert len(x.transport.calls)==1 and len(usage(x))==1
    next_id=restarted.prepare(x.admin,restarted.new_intention(x.admin),'en','short','professional')
    assert next_id!=lid and len(usage(x))==1


def test_site_live_switch_and_existing_runtime_gates_are_independent(qa_case):
    x=qa_case
    path,csrf,_=prepare_http(x);token,_=preview_http(x,path,csrf)
    x.qa.live_enabled=False
    assert x.client.post(path+'/generate',data={'csrf_token':csrf,'review_token':token}).status_code==503
    x.qa.live_enabled=True
    x.qa.runtime.settings=replace(x.settings.ai,kill_switch=True)
    assert x.client.post(path+'/generate',data={'csrf_token':csrf,'review_token':token}).status_code==503
    assert not x.transport.calls and not usage(x)
    assert REAL_DATA_SUPPORTED is False and CURRENT_AI_CONSENT_POLICY.release_state=='DRAFT'


def test_per_actor_generation_rate_limit(tmp_path):
    x=build_case(tmp_path,rate_enabled=True)
    try:
        path,csrf,_=prepare_http(x)
        token,_=preview_http(x,path,csrf)
        data={'csrf_token':csrf,'review_token':token}
        responses=[x.client.post(path+'/generate',data=data) for _ in range(11)]
        assert responses[-1].status_code==429
        assert 'no-store' in responses[-1].headers['Cache-Control']
        assert len(x.transport.calls)==1
    finally:x.db.dispose()
