"""AI-005 owned documents on real disposable SQLite; no external provider calls."""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from domain.cover_letter import LetterError, content, compose, digest
from domain.saved_vacancy import SavedVacancyError
from models import User, SavedVacancy, CareerProfile, CareerProfileVersion
from models.cover_letter import CoverLetter,CoverLetterVersion,CoverLetterProposal
from models.ai import AIUsageEvent
from repositories.cover_letters import CoverLetterRepository
from repositories.profiles import CareerProfileRepository
from repositories.privacy import PrivacyRepository,PrivacySnapshotConflictError
from services.profile import CareerProfileService
from services.cover_letters import CoverLetterService
from tests.test_job001_service import job_env, reference


def profile_payload():
    return {'headline':'Software engineer','summary':'Built REST API tests in Python.',
            'contacts':{'contact_email':'private@example.test','phone':'+123456789'},
            'skills':[{'name':'Python'},{'name':'SQL'},{'name':'Postman'}],
            'employment':[{'company':'Example Studio','position':'Engineer','description':'Prepared 12 reproducible reports in one release; source: test register.'}],
            'achievements':[{'title':'Release testing','description':'Documented steps and expected results.'}]}

@pytest.fixture
def letters(job_env):
    e=job_env
    profile=CareerProfileService(CareerProfileRepository(e.db))
    profile.save(user_id=e.owner,payload=profile_payload(),expected_version=0)
    saved=e.svc.save(e.owner,reference(e)[0])
    e.svc.update_note(e.owner,saved['id'],'Private note must not become a candidate fact',1)
    svc=CoverLetterService(CoverLetterRepository(e.db),signing_key='ai005-test-only')
    return SimpleNamespace(env=e,svc=svc,profile=profile,saved_id=saved['id'],owner=e.owner,other=e.other,db=e.db)


def new(e,**changes):
    data=dict(source_hash=e.svc.source(e.owner,e.saved_id)['source_hash'],operation_key=uuid4().hex,
              language='en',length='short',tone='professional',confirmed=True)
    data.update(changes)
    return e.svc.create(e.owner,e.saved_id,**data)


def save(e,row,body='I would like to discuss the role.',**changes):
    data=dict(expected=row['revision'],subject='Application: Engineer',body=body,
              language='en',length='short',tone='professional',confirmed=True)
    data.update(changes)
    return e.svc.save(e.owner,row['id'],**data)


def proposal(e,row,**changes):
    data=dict(expected=row['revision'],language='en',length='short',tone='professional',
              ids=['profile.summary'],operation_key=uuid4().hex)
    data.update(changes)
    return e.svc.propose_local(e.owner,row['id'],**data)


def test_source_projection_excludes_notes_contacts_ai_and_resume_drafts(letters):
    e=letters;s=e.svc.source(e.owner,e.saved_id)
    encoded=json.dumps(s)
    assert 'private@example.test' not in encoded and '+123456789' not in encoded and 'Private note' not in encoded
    assert s['source']['match'] is None
    assert s['source']['profile_version']==1
    assert 'Built REST API tests in Python.' in encoded
    assert digest(s['source'])==s['source_hash']


def test_create_replay_binding_and_blank_draft(letters):
    e=letters;key=uuid4().hex;a=new(e,operation_key=key);b=new(e,operation_key=key)
    assert a['id']==b['id'] and a['created'] and not b['created']
    assert not a['content']['body'] and a['last_version']==0
    assert e.svc.get(e.owner,a['id'])['versions']==[]
    with pytest.raises(LetterError,match='idempotency_conflict'):new(e,operation_key=key,tone='friendly')


def test_create_requires_confirmation_and_same_source_preview(letters):
    e=letters;source=e.svc.source(e.owner,e.saved_id)
    with pytest.raises(LetterError,match='confirmation_required'):new(e,confirmed=False)
    changed=profile_payload();changed['summary']='New confirmed fact.'
    e.profile.save(user_id=e.owner,payload=changed,expected_version=1)
    with pytest.raises(LetterError,match='stale_source'):new(e,source_hash=source['source_hash'])
    assert e.svc.list(e.owner)['total']==0


def test_no_profile_allows_manual_document_not_fabricated_facts(job_env):
    e=job_env;saved=e.svc.save(e.owner,reference(e)[0])
    svc=CoverLetterService(CoverLetterRepository(e.db),signing_key='test')
    source=svc.source(e.owner,saved['id'])
    assert source['source']['facts']==[] and source['source']['profile_version']==0
    row=svc.create(e.owner,saved['id'],source['source_hash'],uuid4().hex,'en','full','friendly',confirmed=True)
    assert row['last_version']==0
    with pytest.raises(LetterError,match='invalid_selection'):
        svc.propose_local(e.owner,row['id'],1,'en','short','friendly',[],uuid4().hex)


def test_versions_noop_compare_export_and_relogin_storage(letters):
    e=letters;row=new(e);first=save(e,row)
    assert first['last_version']==1 and first['revision']==2
    unchanged=save(e,first);assert not unchanged['changed'] and unchanged['revision']==2
    second=save(e,first,body='A second reviewed version.')
    assert second['last_version']==2
    assert e.svc.version(e.owner,row['id'],1)['content']['body']=='I would like to discuss the role.'
    compared=e.svc.compare(e.owner,row['id'],1,2)
    assert '-I would like' in compared['diff'] and '+A second' in compared['diff']
    assert e.svc.export_text(e.owner,row['id'],1).decode('utf-8-sig').endswith('I would like to discuss the role.\n')
    e.db.dispose();assert e.svc.get(e.owner,row['id'])['last_version']==2
    assert e.profile.get(e.owner).version==1
    assert e.env.svc.get(e.owner,e.saved_id)['note']=='Private note must not become a candidate fact'


def test_stale_editor_and_delete_preserve_newer_version(letters):
    e=letters;row=new(e);current=save(e,row)
    for action in [lambda:save(e,row,body='Stale'),lambda:e.svc.delete(e.owner,row['id'],row['revision'],confirmed=True)]:
        with pytest.raises(LetterError,match='stale_write'):action()
    assert e.svc.get(e.owner,row['id'])['content']==current['content']
    assert len(e.svc.get(e.owner,row['id'])['versions'])==1


@pytest.mark.parametrize('method',['source','get','save','delete','version','export','compose','generate'])
def test_cross_owner_every_entry(letters,method):
    e=letters;row=save(e,new(e));other=e.other
    actions={
        'source':lambda:e.svc.source(other,e.saved_id),'get':lambda:e.svc.get(other,row['id']),
        'save':lambda:e.svc.save(other,row['id'],2,'S','Body','en','short','friendly',confirmed=True),
        'delete':lambda:e.svc.delete(other,row['id'],2,confirmed=True),
        'version':lambda:e.svc.version(other,row['id'],1),'export':lambda:e.svc.export_text(other,row['id'],1),
        'compose':lambda:e.svc.propose_local(other,row['id'],2,'en','short','professional',['profile.summary'],uuid4().hex),
        'generate':lambda:e.svc.generate(other,row['id'])}
    with pytest.raises(LetterError,match='not_found'):actions[method]()
    assert e.svc.list(other)['total']==0


@pytest.mark.parametrize('language',['ru','en'])
@pytest.mark.parametrize('length',['short','full'])
@pytest.mark.parametrize('tone',['professional','friendly'])
def test_local_template_not_ai_explicit_review_and_version(letters,language,length,tone):
    e=letters;row=new(e);p=proposal(e,row,language=language,length=length,tone=tone)
    assert p['origin']=='local_template' and p['status']=='pending'
    assert 'Built REST API tests in Python.' in p['content']['body']
    assert '12' not in p['content']['body']
    assert e.svc.get(e.owner,row['id'])['content']['body']==''
    with pytest.raises(LetterError,match='confirmation_required'):
        e.svc.save(e.owner,row['id'],1,**p['content'],confirmed=False,proposal_id=p['id'])
    result=e.svc.save(e.owner,row['id'],1,**p['content'],confirmed=True,proposal_id=p['id'])
    v=e.svc.version(e.owner,row['id'],1)
    assert v['origin']=='local_template' and v['evidence']['text_unchanged'] is True
    assert result['last_version']==1 and not e.svc.get(e.owner,row['id'])['proposals']
    with e.db.session() as s:assert s.scalar(select(func.count()).select_from(AIUsageEvent))==0


def test_edited_proposal_label_does_not_certify_user_additions(letters):
    e=letters;row=new(e);p=proposal(e,row);value={**p['content'],'body':p['content']['body']+'\nUser revision.'}
    e.svc.save(e.owner,row['id'],1,**value,confirmed=True,proposal_id=p['id'])
    v=e.svc.version(e.owner,row['id'],1)
    assert v['origin']=='user_edited_local_template' and v['evidence']['text_unchanged'] is False
    assert e.profile.get(e.owner).version==1


def test_proposal_replay_and_stale_accept_do_not_overwrite(letters):
    e=letters;row=new(e);key=uuid4().hex;p=proposal(e,row,operation_key=key)
    assert proposal(e,row,operation_key=key)['id']==p['id']
    with pytest.raises(LetterError,match='idempotency_conflict'):proposal(e,row,operation_key=key,tone='friendly')
    current=save(e,row)
    with pytest.raises(LetterError,match='stale_write'):
        e.svc.save(e.owner,row['id'],current['revision'],**p['content'],confirmed=True,proposal_id=p['id'])
    assert e.svc.get(e.owner,row['id'])['content']==current['content']


def test_profile_change_marks_stale_but_never_mutates_history(letters):
    e=letters;row=new(e);p=proposal(e,row)
    payload=profile_payload();payload['summary']='A new profile.'
    e.profile.save(user_id=e.owner,payload=payload,expected_version=1)
    result=e.svc.get(e.owner,row['id']);assert result['source_stale']
    assert result['source']==row['source']
    with pytest.raises(LetterError,match='stale_source'):proposal(e,row)
    with pytest.raises(LetterError,match='stale_source'):
        e.svc.save(e.owner,row['id'],1,**p['content'],confirmed=True,proposal_id=p['id'])
    saved=save(e,row);assert saved['last_version']==1


def test_saved_vacancy_cannot_be_silently_deleted_with_letters(letters):
    e=letters;row=save(e,new(e))
    saved=e.env.svc.get(e.owner,e.saved_id)
    with pytest.raises(SavedVacancyError,match='has_letters'):e.env.svc.delete(e.owner,e.saved_id,saved['revision'])
    e.svc.delete(e.owner,row['id'],row['revision'],confirmed=True)
    e.env.svc.delete(e.owner,e.saved_id,saved['revision'])
    with pytest.raises(SavedVacancyError,match='not_found'):e.env.svc.get(e.owner,e.saved_id)


def test_delete_old_version_preserves_current_and_number_not_reused(letters):
    e=letters;row=save(e,new(e));row=save(e,row,body='Version two.')
    with pytest.raises(LetterError,match='current_version'):e.svc.delete_version(e.owner,row['id'],2,row['revision'],confirmed=True)
    with pytest.raises(LetterError,match='confirmation_required'):e.svc.delete_version(e.owner,row['id'],1,row['revision'],confirmed=False)
    e.svc.delete_version(e.owner,row['id'],1,row['revision'],confirmed=True)
    current=e.svc.get(e.owner,row['id']);assert current['last_version']==2
    with pytest.raises(LetterError,match='not_found'):e.svc.version(e.owner,row['id'],1)
    nextrow=save(e,current,body='Version three.');assert nextrow['last_version']==3


def test_proposal_deletion_owner_and_confirmation(letters):
    e=letters;row=new(e);p=proposal(e,row)
    with pytest.raises(LetterError,match='confirmation_required'):e.svc.reject(e.owner,row['id'],p['id'],1,confirmed=False)
    with pytest.raises(LetterError,match='not_found'):e.svc.reject(e.other,row['id'],p['id'],1,confirmed=True)
    e.svc.reject(e.owner,row['id'],p['id'],1,confirmed=True)
    assert e.svc.get(e.owner,row['id'])['proposals']==[]


def test_privacy_export_and_delete_scopes(letters):
    e=letters;row=save(e,new(e));pending=proposal(e,row)
    repo=PrivacyRepository(e.db)
    exported=repo.export_snapshot(e.owner,expected_password_hash='test-only')
    # Privacy repository returns its snapshot under the same existing contract.
    data=exported.snapshot if hasattr(exported,'snapshot') else exported
    if isinstance(data,tuple):data=data[0]
    assert len(data['cover_letters'])==1 and len(data['cover_letter_versions'])==1 and len(data['cover_letter_proposals'])==1
    raw=json.dumps(data['cover_letters'])
    assert 'operation_hash' not in raw and 'request_hash' not in raw and 'private@example.test' not in raw
    other=repo.export_snapshot(e.other,expected_password_hash='test-only')
    other=other.snapshot if hasattr(other,'snapshot') else other
    if isinstance(other,tuple):other=other[0]
    assert other['cover_letters']==[]
    e.svc.delete(e.owner,row['id'],row['revision'],confirmed=True)
    for model in (CoverLetter,CoverLetterVersion,CoverLetterProposal):
        with e.db.session() as s:assert s.scalar(select(func.count()).select_from(model))==0
    assert e.env.svc.get(e.owner,e.saved_id)


def test_account_delete_cascades_letters_versions_proposals(letters):
    e=letters;row=save(e,new(e));proposal(e,row)
    with e.db.session() as s,s.begin():s.execute(delete(User).where(User.id==e.owner))
    with e.db.session() as s:
        for model in (CoverLetter,CoverLetterVersion,CoverLetterProposal):
            assert s.scalar(select(func.count()).select_from(model).where(model.user_id==e.owner))==0
        assert s.get(User,e.other)


def test_ownership_enforced_by_composite_foreign_key(letters):
    e=letters;row=new(e)
    with e.db.session() as s:
        entity=s.get(CoverLetter,row['id']);entity.user_id=e.other
        with pytest.raises(IntegrityError):s.commit()
        s.rollback()


def test_real_generation_closed_even_with_enabled_environment(letters,monkeypatch):
    e=letters;row=new(e)
    for k,v in {'AI_ENABLED':'1','AI_KILL_SWITCH':'0','AI_SYNTHETIC_ACCESS_ENABLED':'1','AI_LEGAL_APPROVED':'1'}.items():monkeypatch.setenv(k,v)
    with pytest.raises(LetterError,match='generation_unavailable'):e.svc.generate(e.owner,row['id'])
    with e.db.session() as s:assert s.scalar(select(func.count()).select_from(AIUsageEvent))==0


def test_parallel_create_and_edit_preserve_one_result(letters):
    e=letters;key=uuid4().hex
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda _:new(e,operation_key=key),range(4)))
    assert len({r['id'] for r in rows})==1
    row=rows[0]
    def edit(n):
        try:return save(e,row,body='Parallel '+str(n))['last_version']
        except LetterError as exc:return str(exc)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(edit,range(4)))
    assert results.count(1)==1 and results.count('stale_write')==3


@pytest.mark.parametrize('field,value', [('body',''),('body','x'*8001),('subject','x'*241),('body','Bad\x00'),('subject','a\nb'),('language','fr'),('length','huge'),('tone','aggressive')])
def test_bounded_editor_rejects_invalid_input(letters,field,value):
    e=letters;row=new(e)
    with pytest.raises(LetterError):save(e,row,**{field:value})
    assert e.svc.get(e.owner,row['id'])['last_version']==0


@pytest.mark.parametrize('ids',[[],['missing'],['profile.summary','profile.summary'],['profile.summary']*9])
def test_invalid_selection_never_creates_a_proposal(letters,ids):
    e=letters;row=new(e)
    with pytest.raises(LetterError,match='invalid_selection'):proposal(e,row,ids=ids)
    assert e.svc.get(e.owner,row['id'])['proposals']==[]


def test_tampered_snapshot_and_version_are_fail_closed(letters):
    e=letters;row=save(e,new(e))
    with e.db.session() as s,s.begin():s.scalar(select(CoverLetterVersion).where(CoverLetterVersion.letter_id==row['id'])).content_json='{}'
    with pytest.raises(LetterError,match='storage_integrity'):e.svc.version(e.owner,row['id'],1)
    with e.db.session() as s,s.begin():s.get(CoverLetter,row['id']).source_json='{}'
    with pytest.raises(LetterError,match='storage_integrity'):e.svc.get(e.owner,row['id'])
