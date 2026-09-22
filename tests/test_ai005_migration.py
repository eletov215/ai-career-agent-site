"""AI-005 additive migration and populated ownership/cascade semantics."""
import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4
import pytest
from alembic import command
from sqlalchemy import inspect,select,delete,func
from database import create_database,upgrade_database,downgrade_database,current_revision,alembic_config
from models import User,SearchSnapshot,SavedVacancy
from models.cover_letter import CoverLetter,CoverLetterVersion,CoverLetterProposal
from repositories.saved_vacancies import SavedVacancyRepository
from repositories.cover_letters import CoverLetterRepository
from services.saved_vacancies import SavedVacancyService
from services.cover_letters import CoverLetterService
from tests.test_job001_service import reference
from domain.cover_letter import LetterError

TABLES={'cover_letters','cover_letter_versions','cover_letter_proposals'}


def test_0020_round_trip_metadata_preserves_existing_saved_and_users(tmp_path):
    url=f'sqlite:///{tmp_path}/migration.db';upgrade_database(url,'20260917_0019');db=create_database(url)
    before=set(inspect(db.engine).get_table_names());uid=str(uuid4())
    with db.session() as s,s.begin():s.add(User(id=uid,status='active',email_verified_at=1,created_at=1,updated_at=1))
    savedsvc=SavedVacancyService(SavedVacancyRepository(db),signing_key='test-only')
    e=SimpleNamespace(db=db,owner=uid,svc=savedsvc);saved=savedsvc.save(uid,reference(e)[0])
    upgrade_database(url,'20260917_0020');assert current_revision(db.engine)=='20260917_0020'
    assert set(inspect(db.engine).get_table_names())-before==TABLES
    command.check(alembic_config(url));upgrade_database(url)
    svc=CoverLetterService(CoverLetterRepository(db),signing_key='test')
    src=svc.source(uid,saved['id'])
    row=svc.create(uid,saved['id'],src['source_hash'],uuid4().hex,'en','short','professional',confirmed=True)
    svc.save(uid,row['id'],1,'Subject','Body','en','short','professional',confirmed=True)
    downgrade_database(url,'20260917_0019')
    assert set(inspect(db.engine).get_table_names())==before
    with db.session() as s:assert s.get(User,uid) and s.get(SavedVacancy,saved['id'])
    upgrade_database(url);command.check(alembic_config(url));assert svc.list(uid)['total']==0
    db.dispose()


@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'),reason='Disposable PostgreSQL needed; skipped is not a pass')
def test_postgresql_ownership_concurrency_versioning_and_cascade():
    url=os.environ['POSTGRES_TEST_URL'];upgrade_database(url);db=create_database(url)
    uid,other=str(uuid4()),str(uuid4());sid=None
    try:
        with db.session() as s,s.begin():
            for user in (uid,other):s.add(User(id=user,status='active',email_verified_at=1,created_at=1,updated_at=1))
        savedsvc=SavedVacancyService(SavedVacancyRepository(db),signing_key='test')
        e=SimpleNamespace(db=db,owner=uid,svc=savedsvc)
        token,sid,_=reference(e);saved=savedsvc.save(uid,token)
        svc=CoverLetterService(CoverLetterRepository(db),signing_key='test')
        source=svc.source(uid,saved['id']);key=uuid4().hex
        def create(_):return svc.create(uid,saved['id'],source['source_hash'],key,'en','full','friendly',confirmed=True)
        with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(create,range(4)))
        assert len({r['id'] for r in rows})==1
        row=rows[0];current=svc.save(uid,row['id'],1,'Subject','Reviewed body','en','full','friendly',confirmed=True)
        with pytest.raises(LetterError,match='stale_write'):svc.save(uid,row['id'],1,'Subject','Other','en','full','friendly',confirmed=True)
        with pytest.raises(LetterError,match='not_found'):svc.version(other,row['id'],1)
        db.dispose();assert svc.export_text(uid,row['id'],1).endswith(b'Reviewed body\n')
        with db.session() as s,s.begin():s.execute(delete(User).where(User.id==uid))
        with db.session() as s:
            for model in (CoverLetter,CoverLetterVersion,CoverLetterProposal):assert s.scalar(select(func.count()).select_from(model).where(model.user_id==uid))==0
    finally:
        with db.session() as s,s.begin():
            s.execute(delete(User).where(User.id.in_([uid,other])))
            if sid:s.execute(delete(SearchSnapshot).where(SearchSnapshot.id==sid))
        db.dispose()
