"""JOB-002 state, atomic history, isolation, cascade and privacy coverage."""
from types import SimpleNamespace
from uuid import uuid4
import pytest
from sqlalchemy import delete, func, select
from database import create_database, upgrade_database
from domain.application_tracker import STATES, TRANSITIONS, TrackerError
from domain.saved_vacancy import canonical_json, fingerprint
from models import User, SavedVacancy, SavedVacancyTracker, SavedVacancyTrackerEvent
from repositories.application_trackers import ApplicationTrackerRepository
from repositories.privacy import PrivacyRepository
from services.application_trackers import ApplicationTrackerService


@pytest.fixture
def tracker_env(tmp_path):
    url=f'sqlite:///{tmp_path}/tracker.db';upgrade_database(url);db=create_database(url)
    owner,other,saved=str(uuid4()),str(uuid4()),str(uuid4())
    with db.session() as s,s.begin():
        for uid in (owner,other):
            s.add(User(id=uid,status='active',email_verified_at=1,password_hash='hash',created_at=1,updated_at=1))
        s.flush()
        snapshot={'snapshot_version':'saved-vacancy-v1'}
        s.add(SavedVacancy(id=saved,user_id=owner,snapshot_json=canonical_json(snapshot),snapshot_hash=fingerprint(snapshot),
            snapshot_version='saved-vacancy-v1',title='Role',company='Co',location='Remote',search_text='role',
            note='',revision=1,created_at=1,updated_at=1))
    yield SimpleNamespace(db=db,owner=owner,other=other,saved=saved,
        svc=ApplicationTrackerService(ApplicationTrackerRepository(db)))
    db.dispose()


def test_virtual_saved_first_transition_noop_refresh_and_stale_conflict(tracker_env):
    e=tracker_env
    assert e.svc.get(e.owner,e.saved)=={'state':'saved','revision':0,'created_at':None,'updated_at':None,'events':[]}
    assert e.svc.transition(e.owner,e.saved,'saved',0,now=5)['revision']==0
    first=e.svc.transition(e.owner,e.saved,'preparing',0,now=6)
    assert (first['state'],first['revision'])==('preparing',1)
    reread=e.svc.get(e.owner,e.saved);assert len(reread['events'])==1
    assert reread['events'][0]['from_state']=='saved'
    assert e.svc.transition(e.owner,e.saved,'preparing',1,now=7)['revision']==1
    with pytest.raises(TrackerError,match='stale_write'):
        e.svc.transition(e.owner,e.saved,'closed',0,now=8)
    assert e.svc.get(e.owner,e.saved)['state']=='preparing'
    with e.db.session() as s:
        assert s.scalar(select(func.count()).select_from(SavedVacancyTrackerEvent))==1


def test_every_allowed_and_disallowed_transition():
    allowed={(source,target) for source,targets in TRANSITIONS.items() for target in targets}
    from domain.application_tracker import validate_transition
    for source in STATES:
        assert validate_transition(source,source) is False
        for target in STATES:
            if source==target:continue
            if (source,target) in allowed:assert validate_transition(source,target)
            else:
                with pytest.raises(TrackerError,match='invalid_transition'):validate_transition(source,target)


def test_later_transition_revision_events_owner_isolation_and_cascades(tracker_env):
    e=tracker_env;e.svc.transition(e.owner,e.saved,'submitted_user_reported',0,now=10)
    second=e.svc.transition(e.owner,e.saved,'in_process_user_reported',1,now=10)
    assert second['revision']==2
    history=e.svc.get(e.owner,e.saved)['events']
    assert [(event['event_revision'],event['from_state'],event['to_state']) for event in history]==[
        (2,'submitted_user_reported','in_process_user_reported'),
        (1,'saved','submitted_user_reported')]
    with pytest.raises(TrackerError,match='not_found'):e.svc.get(e.other,e.saved)
    with pytest.raises(TrackerError,match='not_found'):e.svc.transition(e.other,e.saved,'closed',2,now=12)
    snapshot,_=PrivacyRepository(e.db).export_snapshot(e.owner,expected_password_hash='hash')
    other,_=PrivacyRepository(e.db).export_snapshot(e.other,expected_password_hash='hash')
    assert len(snapshot['saved_vacancy_trackers'])==1 and len(snapshot['saved_vacancy_tracker_events'])==2
    assert other['saved_vacancy_trackers']==other['saved_vacancy_tracker_events']==[]
    with e.db.session() as s,s.begin():s.execute(delete(SavedVacancy).where(SavedVacancy.id==e.saved))
    with e.db.session() as s:
        assert s.scalar(select(func.count()).select_from(SavedVacancyTracker))==0
        assert s.scalar(select(func.count()).select_from(SavedVacancyTrackerEvent))==0


def test_account_delete_cascades_tracker_subtree(tracker_env):
    e=tracker_env;e.svc.transition(e.owner,e.saved,'closed',0,now=10)
    counts=PrivacyRepository(e.db).delete_account(
        e.owner,expected_password_hash='hash',now=11)
    assert counts['saved_vacancy_trackers']==1
    assert counts['saved_vacancy_tracker_events']==1
    with e.db.session() as s:
        assert s.get(User,e.owner) is None
        assert s.scalar(select(func.count()).select_from(SavedVacancyTracker))==0
        assert s.scalar(select(func.count()).select_from(SavedVacancyTrackerEvent))==0
