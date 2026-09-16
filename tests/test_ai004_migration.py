"""AI-004 additive schema and disposable PostgreSQL integration."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import os
import pytest
from sqlalchemy import inspect, select, delete
from alembic import command
from database import CURRENT_REVISION, create_database, upgrade_database, downgrade_database, current_revision, alembic_config
from models import User, ResumeDraft
from repositories.vacancy_match import VacancyMatchRepository
from services.vacancy_match import VacancyMatchService
from domain.vacancy_match import MatchError
from tests.test_ai004_service import req

NEW_TABLES={'vacancy_match_reports','vacancy_match_series'}


def test_0018_roundtrip_is_additive_preserves_users_and_metadata(tmp_path):
    url=f'sqlite:///{tmp_path}/migration.db';upgrade_database(url,'20260916_0017');db=create_database(url)
    old=set(inspect(db.engine).get_table_names());owner=str(uuid4())
    with db.session() as session,session.begin():session.add(User(id=owner,status='active',email_verified_at=1,created_at=1,updated_at=1))
    upgrade_database(url)
    assert current_revision(db.engine)==CURRENT_REVISION=='20260916_0018'
    assert set(inspect(db.engine).get_table_names())-old==NEW_TABLES
    command.check(alembic_config(url))
    svc=VacancyMatchService(VacancyMatchRepository(db),None,fingerprint_key='test')
    report=svc.create_reference(req((db,owner,'',svc)))
    upgrade_database(url)
    assert svc.get(owner,report['id'])['version']==1
    downgrade_database(url,'20260916_0017')
    assert set(inspect(db.engine).get_table_names())==old
    with db.session() as session:assert session.get(User,owner)
    upgrade_database(url);command.check(alembic_config(url))
    assert not svc.history(owner)
    db.dispose()


@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'),reason='Disposable PostgreSQL service required in CI')
def test_postgresql_match_concurrency_owner_cascade_and_reconnect():
    url=os.environ['POSTGRES_TEST_URL'];upgrade_database(url);db=create_database(url)
    owner,other=str(uuid4()),str(uuid4())
    with db.session() as session,session.begin():
        for uid in (owner,other):session.add(User(id=uid,status='active',email_verified_at=1,created_at=1,updated_at=1))
    svc=VacancyMatchService(VacancyMatchRepository(db),None,fingerprint_key='test')
    env=(db,owner,other,svc)
    try:
        request=req(env)
        with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda _:svc.create_reference(request),range(4)))
        assert len({r['id'] for r in rows})==1
        with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(lambda _:svc.create_reference(req(env)),range(3)))
        assert sorted(r['version'] for r in rows)==[2,3,4]
        with pytest.raises(MatchError):svc.get(other,rows[0]['id'])
        db.dispose();assert svc.get(owner,rows[0]['id'])['origin']=='reference'
        assert NEW_TABLES<=set(inspect(db.engine).get_table_names())
    finally:
        with db.session() as session,session.begin():session.execute(delete(User).where(User.id.in_([owner,other])))
        db.dispose()
