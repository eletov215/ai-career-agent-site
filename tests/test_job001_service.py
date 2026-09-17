"""JOB-001 real SQLite persistence, source authority, privacy and concurrency."""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from database import create_database, upgrade_database
from domain.saved_vacancy import SavedVacancyError, fingerprint, canonical_json, safe_source_url, note_value, revision_value, legacy_keys
from models import User, SearchSnapshot, SearchSnapshotItem, SavedVacancy, SavedVacancySource, Vacancy, VacancySourceRecord, CareerProfile, ResumeDraft
from models.ai import AIUsageEvent
from repositories.saved_vacancies import SavedVacancyRepository
from repositories.privacy import PrivacyRepository, PrivacySnapshotConflictError
from services.saved_vacancies import SavedVacancyService
from services.saved_vacancy_snapshot import build_snapshot


def payload(external_id='123', source='hh', **extra):
    roots={'hh':'https://hh.ru/vacancy/','reed':'https://www.reed.co.uk/jobs/','superjob':'https://www.superjob.ru/vakansii/','trudvsem':'https://trudvsem.ru/vacancy/'}
    return {'source':source,'external_id':external_id,'url':roots.get(source,'https://example.invalid/')+external_id,
            'source_title':source,'title':'Python Developer','company':'Example Ltd',
            'location':'Remote','description':'Maintain APIs.','requirements':'Python, SQL',
            'salary_from':100,'salary_to':200,'currency':'EUR','work_format':'remote',
            'employment_code':'full','experience_code':'unknown','source_status':'active', **extra}


def add_search(db, raw, now=None):
    now=int(time.time()) if now is None else now
    sid,key=str(uuid4()),fingerprint(raw)[:40]
    with db.session() as session,session.begin():
        session.add(SearchSnapshot(id=sid,query_fingerprint='0'*64,selected_sources_json='["hh"]',sort_code='date',
            page_size=20,committed_count=1,known_unique_total=1,created_at=now,updated_at=now,expires_at=now+3600))
        session.flush()
        session.add(SearchSnapshotItem(snapshot_id=sid,ordinal=0,stable_key=key,source_keys_json='[]',
            payload_json=canonical_json(raw),created_at=now,updated_at=now))
    return sid,key


def reference(env, raw=None, user=None):
    raw=payload() if raw is None else raw
    sid,key=add_search(env.db,raw)
    ctrl=env.svc.controls(user or env.owner,sid,[{**raw,'_snapshot_item_key':key}])[0]
    return ctrl['reference'],sid,key


@pytest.fixture
def job_env(tmp_path):
    url=f'sqlite:///{tmp_path}/job.db';upgrade_database(url);db=create_database(url)
    owner,other=str(uuid4()),str(uuid4())
    with db.session() as session,session.begin():
        for uid in (owner,other):
            session.add(User(id=uid,status='active',email_verified_at=1,password_hash='test-only',created_at=1,updated_at=1))
    svc=SavedVacancyService(SavedVacancyRepository(db),signing_key='test-only-job-key')
    yield SimpleNamespace(db=db,owner=owner,other=other,svc=svc,url=url)
    db.dispose()


def test_server_snapshot_persists_after_cache_cleanup_and_reconnect(job_env):
    e=job_env;token,sid,key=reference(e);row=e.svc.save(e.owner,token)
    assert row['created'] and row['revision']==1
    with e.db.session() as session,session.begin():session.execute(delete(SearchSnapshot).where(SearchSnapshot.id==sid))
    e.db.dispose()
    kept=e.svc.get(e.owner,row['id']);assert kept['snapshot']==row['snapshot']
    assert kept['sources'][0]['state']=='not_in_cache'
    assert kept['match'] is None
    with e.db.session() as session:
        for model in (CareerProfile,ResumeDraft,AIUsageEvent,Vacancy):
            assert session.scalar(select(func.count()).select_from(model))==0


def test_repeat_and_parallel_save_create_only_one_snapshot(job_env):
    e=job_env;token,_,_=reference(e)
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda _:e.svc.save(e.owner,token),range(4)))
    assert len({row['id'] for row in rows})==1
    assert sum(row['created'] for row in rows)==1
    again,_,_=reference(e,payload(description='Changed source description'))
    saved=e.svc.save(e.owner,again)
    assert not saved['created'] and saved['snapshot']['description']=='Maintain APIs.'
    assert e.svc.list(e.owner)['total']==1


def test_owner_reference_and_read_edit_delete_export_are_isolated(job_env):
    e=job_env;token,_,_=reference(e);row=e.svc.save(e.owner,token)
    with pytest.raises(SavedVacancyError,match='invalid_reference'):e.svc.save(e.other,token)
    for action in (lambda:e.svc.get(e.other,row['id']),lambda:e.svc.update_note(e.other,row['id'],'text',1),lambda:e.svc.delete(e.other,row['id'],1)):
        with pytest.raises(SavedVacancyError,match='not_found'):action()
    assert e.svc.list(e.other)['total']==0
    p=PrivacyRepository(e.db)
    data,_=p.export_snapshot(e.owner,expected_password_hash='test-only')
    other,_=p.export_snapshot(e.other,expected_password_hash='test-only')
    assert [r['id'] for r in data['saved_vacancies']]==[row['id']]
    assert data['saved_vacancy_sources'][0]['saved_vacancy_id']==row['id']
    assert other['saved_vacancies']==other['saved_vacancy_sources']==[]
    assert 'test-only-job-key' not in json.dumps(data)


@pytest.mark.parametrize('change',['expired','uncommitted','changed','deleted'])
def test_expired_changed_missing_or_unserved_search_items_fail_closed(job_env,change):
    e=job_env;token,sid,key=reference(e)
    with e.db.session() as session,session.begin():
        if change=='expired':session.get(SearchSnapshot,sid).expires_at=1
        if change=='uncommitted':session.get(SearchSnapshot,sid).committed_count=0
        if change=='deleted':session.execute(delete(SearchSnapshot).where(SearchSnapshot.id==sid))
        if change=='changed':
            item=session.scalar(select(SearchSnapshotItem).where(SearchSnapshotItem.snapshot_id==sid))
            item.payload_json=canonical_json(payload(title='Different job'))
    with pytest.raises(SavedVacancyError,match='stale_source'):e.svc.save(e.owner,token)
    assert e.svc.list(e.owner)['total']==0


@pytest.mark.parametrize('value',['',None,42,'x'*4097,'malformed.signature'])
def test_invalid_signed_reference_is_rejected(job_env,value):
    with pytest.raises(SavedVacancyError):job_env.svc.save(job_env.owner,value)


def test_signed_reference_expiration_and_tampering(job_env,monkeypatch):
    e=job_env;token,_,_=reference(e)
    with pytest.raises(SavedVacancyError):e.svc.save(e.owner,token+'tampered')
    from itsdangerous import TimestampSigner
    current=int(time.time());monkeypatch.setattr(TimestampSigner,'get_timestamp',lambda _self:current+1900)
    with pytest.raises(SavedVacancyError,match='invalid_reference'):e.svc.save(e.owner,token)


@pytest.mark.parametrize('status,verified',[('pending',None),('suspended',1),('active',None)])
def test_inactive_or_unverified_owner_cannot_mutate(job_env,status,verified):
    e=job_env;token,_,_=reference(e)
    with e.db.session() as session,session.begin():
        user=session.get(User,e.owner);user.status=status;user.email_verified_at=verified
    with pytest.raises(SavedVacancyError,match='verified_account_required'):e.svc.save(e.owner,token)


def test_notes_noop_conflict_and_stale_delete_preserve_newer_content(job_env):
    e=job_env;token,_,_=reference(e);row=e.svc.save(e.owner,token)
    note='\u041e\u0431\u0441\u0443\u0434\u0438\u0442\u044c \u0437\u0430\u0440\u043f\u043b\u0430\u0442\u0443\n<script>literal text</script>'
    fresh=e.svc.update_note(e.owner,row['id'],note,1);assert fresh['revision']==2
    assert e.svc.update_note(e.owner,row['id'],note,'2')['revision']==2
    with pytest.raises(SavedVacancyError,match='stale_write'):e.svc.update_note(e.owner,row['id'],'losing text',1)
    with pytest.raises(SavedVacancyError,match='stale_write'):e.svc.delete(e.owner,row['id'],1)
    assert e.svc.get(e.owner,row['id'])['note']==note
    assert e.svc.list(e.owner,query='\u041e\u0411\u0421\u0423\u0414\u0418\u0422\u042c')['total']==1
    assert e.svc.get(e.owner,row['id'])['snapshot_hash']==row['snapshot_hash']


def test_parallel_notes_one_revision_wins(job_env):
    e=job_env;token,_,_=reference(e);row=e.svc.save(e.owner,token)
    def update(value):
        try:return e.svc.update_note(e.owner,row['id'],value,1)['note']
        except SavedVacancyError as exc:return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(update,['one','two']))
    assert outcomes.count('stale_write')==1
    assert e.svc.get(e.owner,row['id'])['revision']==2


def test_delete_removes_only_owned_snapshot_and_aliases_and_resave_gets_new_id(job_env):
    e=job_env;t1,_,_=reference(e);one=e.svc.save(e.owner,t1)
    t2,_,_=reference(e,payload('456'));two=e.svc.save(e.owner,t2)
    e.svc.delete(e.owner,one['id'],1)
    with pytest.raises(SavedVacancyError,match='not_found'):e.svc.get(e.owner,one['id'])
    assert e.svc.get(e.owner,two['id'])
    again=e.svc.save(e.owner,t1);assert again['id']!=one['id']
    with e.db.session() as session:
        assert session.scalar(select(func.count()).select_from(SavedVacancySource).where(SavedVacancySource.saved_vacancy_id==one['id']))==0


def test_dedup_source_aliases_share_snapshot_without_overwriting_note(job_env):
    e=job_env;t,_,_=reference(e);one=e.svc.save(e.owner,t)
    e.svc.update_note(e.owner,one['id'],'keep me',1)
    combined=payload(description='new primary',source_records=[payload(),payload('456','reed')])
    t,_,_=reference(e,combined);two=e.svc.save(e.owner,t)
    assert two['id']==one['id'] and two['note']=='keep me'
    assert two['snapshot']['description']=='Maintain APIs.'
    t,_,_=reference(e,payload('456','reed'));assert e.svc.save(e.owner,t)['id']==one['id']
    assert len(e.svc.get(e.owner,one['id'])['sources'])==2


def test_ambiguous_group_does_not_merge_two_existing_notes(job_env):
    e=job_env;ids=[]
    for raw in (payload(),payload('456','reed')):
        t,_,_=reference(e,raw);ids.append(e.svc.save(e.owner,t)['id'])
    t,_,_=reference(e,payload(source_records=[payload(),payload('456','reed')]))
    with pytest.raises(SavedVacancyError,match='ambiguous_group'):e.svc.save(e.owner,t)
    assert e.svc.list(e.owner)['total']==2


def test_source_cache_state_is_not_misrepresented_as_live_probe(job_env):
    e=job_env;t,_,_=reference(e);row=e.svc.save(e.owner,t)
    cid=str(uuid4());now=int(time.time())
    with e.db.session() as session,session.begin():
        session.add(Vacancy(id=cid,title='Cached',created_at=now,updated_at=now));session.flush()
        session.add(VacancySourceRecord(vacancy_id=cid,source='hh',external_id='123',title='Cached',
            source_status='active',first_seen_at=now,last_seen_at=now,fetched_at=now,updated_at=now))
    assert e.svc.get(e.owner,row['id'],now=now)['sources'][0]['state']=='active_in_cache'
    assert e.svc.get(e.owner,row['id'],now=now+90000)['sources'][0]['state']=='stale_cache'
    with e.db.session() as session,session.begin():
        src=session.scalar(select(VacancySourceRecord).where(VacancySourceRecord.vacancy_id==cid));src.source_status='closed'
    assert e.svc.get(e.owner,row['id'])['sources'][0]['state']=='closed_in_cache'
    with e.db.session() as session,session.begin():session.execute(delete(Vacancy).where(Vacancy.id==cid))
    assert e.svc.get(e.owner,row['id'])['sources'][0]['state']=='not_in_cache'
    assert e.svc.get(e.owner,row['id'])['snapshot']==row['snapshot']


def test_server_snapshot_allowlist_excludes_raw_secrets_and_marks_truncation():
    snap=build_snapshot(payload(raw_json='private-token',access_token='secret',description='X'*33000,
                              url='https://hh.ru/vacancy/123?token=secret#fragment'))
    assert snap['source_records'][0]['url']=='https://hh.ru/vacancy/123'
    assert 'secret' not in canonical_json(snap) and 'raw_json' not in snap
    assert len(snap['description'])==32000 and 'description' in snap['truncated_fields']


@pytest.mark.parametrize('url',[
    'javascript:alert(1)','//hh.ru/vacancy/1','https://hh.ru.evil.test/1',
    'https://user:pass@hh.ru/vacancy/1','https://evil.test/1','https://127.0.0.1/1',
    'https://hh.ru:444/1','https://hh.ru/\\evil','https://hh.ru/\nabc','https://hh.ru/%0aabc',
    'https://hh.ru/%5cevil','https://[::1]/1',None,123,
])
def test_unsafe_links_are_not_renderable(url):
    assert safe_source_url(url,'hh')==''


@pytest.mark.parametrize('raw',[
    payload(source='other'),payload(external_id='',url='javascript:test'),payload(title=''),
    payload(source_records=[{'source':'hh','external_id':'x'*257}]),
    payload(source_records=[payload(str(i)) for i in range(17)]),
])
def test_unsupported_source_data_cannot_be_saved(raw):
    with pytest.raises(SavedVacancyError):build_snapshot(raw)


@pytest.mark.parametrize('value',[True,False,0,-1,'-1','0','1.0','01','1e3',None,2147483648])
def test_revision_is_bounded_positive_integer(value):
    with pytest.raises(SavedVacancyError):revision_value(value)


@pytest.mark.parametrize('value',['x'*4001,'bad\x00text',None,[],42])
def test_invalid_notes_are_rejected(value):
    with pytest.raises(SavedVacancyError):note_value(value)


def test_legacy_only_explicit_exact_matches_and_partial_results(job_env):
    e=job_env;raw=payload();add_search(e.db,raw)
    assert e.svc.list(e.owner)['total']==0  # Reading never migrates.
    result=e.svc.import_legacy(e.owner,[raw['url'],'not-found'])
    assert result=={'saved_keys':[raw['url']],'saved_count':1,'unresolved_count':1}
    assert e.svc.import_legacy(e.owner,[raw['url']])['saved_count']==1
    assert e.svc.list(e.owner)['total']==1


@pytest.mark.parametrize('keys',[[],['x']*51,[42],None,['x'*2049],['\x00'],['']])
def test_invalid_legacy_import_inputs_fail_closed(keys):
    with pytest.raises(SavedVacancyError):legacy_keys(keys)


def test_limit_search_paging_and_literal_wildcards(job_env,monkeypatch):
    e=job_env
    for number in range(23):
        t,_,_=reference(e,payload(str(number),title=f'Role {number:02}'));e.svc.save(e.owner,t)
    one=e.svc.list(e.owner);two=e.svc.list(e.owner,page=2)
    assert one['total']==23 and len(one['items'])==20 and len(two['items'])==3
    assert not {x['id'] for x in one['items']}&{x['id'] for x in two['items']}
    assert e.svc.list(e.owner,query='Role 0')['total']==10
    assert e.svc.list(e.owner,query='%')['total']==0
    assert e.svc.list(e.owner,query="' OR 1=1 --")['total']==0
    monkeypatch.setattr('repositories.saved_vacancies.MAX_SAVED',23)
    t,_,_=reference(e,payload('extra'))
    with pytest.raises(SavedVacancyError,match='history_limit'):e.svc.save(e.owner,t)
    t,_,_=reference(e,payload('0'));assert not e.svc.save(e.owner,t)['created']


def test_composite_owner_fk_and_user_deletion_cascade(job_env):
    e=job_env;t,_,_=reference(e);row=e.svc.save(e.owner,t)
    with pytest.raises(IntegrityError):
        with e.db.session() as session,session.begin():
            session.add(SavedVacancySource(id=str(uuid4()),saved_vacancy_id=row['id'],user_id=e.other,
                source='reed',external_id='bad',identity_hash='0'*64,url='',created_at=1))
    with e.db.session() as session,session.begin():session.execute(delete(User).where(User.id==e.owner))
    with e.db.session() as session:
        assert session.scalar(select(func.count()).select_from(SavedVacancy))==0
        assert session.scalar(select(func.count()).select_from(SavedVacancySource))==0
        assert session.get(User,e.other)


def test_corrupt_snapshot_fails_read_and_export(job_env):
    e=job_env;t,_,_=reference(e);row=e.svc.save(e.owner,t)
    with e.db.session() as session,session.begin():session.get(SavedVacancy,row['id']).snapshot_json='{}'
    with pytest.raises(SavedVacancyError,match='invalid_saved_snapshot'):e.svc.get(e.owner,row['id'])
    with pytest.raises(PrivacySnapshotConflictError):PrivacyRepository(e.db).export_snapshot(e.owner,expected_password_hash='test-only')
