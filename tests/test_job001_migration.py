"""Additive 0019/0018 round trip and mandatory disposable PostgreSQL checks."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
import pytest
from alembic import command
from sqlalchemy import delete, inspect, select, func
from database import CURRENT_REVISION, alembic_config, create_database, current_revision, downgrade_database, upgrade_database
from models import User, SavedVacancy, SavedVacancySource, SearchSnapshot
from domain.saved_vacancy import SavedVacancyError
from repositories.saved_vacancies import SavedVacancyRepository
from services.saved_vacancies import SavedVacancyService
from tests.test_job001_service import reference

TABLES = {'saved_vacancies','saved_vacancy_sources'}


def test_0019_additive_roundtrip_metadata_and_repeat_upgrade(tmp_path):
    url=f'sqlite:///{tmp_path}/migrate.db';upgrade_database(url,'20260916_0018');db=create_database(url)
    before=set(inspect(db.engine).get_table_names());owner=str(uuid4())
    with db.session() as s,s.begin():s.add(User(id=owner,status='active',email_verified_at=1,created_at=1,updated_at=1))
    upgrade_database(url,'20260917_0019')
    assert current_revision(db.engine)=='20260917_0019'
    assert set(inspect(db.engine).get_table_names())-before==TABLES
    # Metadata-to-head validation is exercised after the final upgrade below.
    env=SimpleNamespace(db=db,owner=owner,svc=SavedVacancyService(SavedVacancyRepository(db),signing_key='test-only'))
    token,sid,key=reference(env);row=env.svc.save(owner,token)
    upgrade_database(url,'20260917_0019');assert env.svc.get(owner,row['id'])
    downgrade_database(url,'20260916_0018')
    assert set(inspect(db.engine).get_table_names())==before
    with db.session() as s:assert s.get(User,owner) and s.get(SearchSnapshot,sid)
    upgrade_database(url);command.check(alembic_config(url));assert env.svc.list(owner)['total']==0
    db.dispose()


@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'),reason='Disposable PostgreSQL service required; skipped != passed')
def test_postgresql_concurrent_save_conflict_reconnect_owner_cascade():
    url=os.environ['POSTGRES_TEST_URL'];upgrade_database(url);db=create_database(url)
    owner,other=str(uuid4()),str(uuid4());sid=None
    with db.session() as s,s.begin():
        for uid in (owner,other):s.add(User(id=uid,status='active',email_verified_at=1,created_at=1,updated_at=1))
    svc=SavedVacancyService(SavedVacancyRepository(db),signing_key='test-only');e=SimpleNamespace(db=db,owner=owner,svc=svc)
    try:
        token,sid,_=reference(e)
        with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda _:svc.save(owner,token),range(4)))
        assert len({row['id'] for row in rows})==1
        row=rows[0];svc.update_note(owner,row['id'],'first',1)
        with pytest.raises(SavedVacancyError,match='stale_write'):svc.update_note(owner,row['id'],'second',1)
        with pytest.raises(SavedVacancyError,match='not_found'):svc.get(other,row['id'])
        db.dispose();assert svc.get(owner,row['id'])['note']=='first'
        with db.session() as s,s.begin():s.execute(delete(User).where(User.id==owner))
        with db.session() as s:
            assert s.scalar(select(func.count()).select_from(SavedVacancy).where(SavedVacancy.user_id==owner))==0
            assert s.scalar(select(func.count()).select_from(SavedVacancySource).where(SavedVacancySource.user_id==owner))==0
    finally:
        with db.session() as s,s.begin():
            s.execute(delete(User).where(User.id.in_([owner,other])))
            if sid:s.execute(delete(SearchSnapshot).where(SearchSnapshot.id==sid))
        db.dispose()
