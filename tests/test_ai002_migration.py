from uuid import uuid4
import os
import time
import pytest
from sqlalchemy import inspect,select,delete
from database import create_database,upgrade_database,downgrade_database,current_revision,alembic_config
from models import User
from models.resume_analysis import ResumeAnalysisReport
from repositories.resume_analysis import ResumeAnalysisRepository
from repositories.ai import AIRepository
from services.resume_analysis import ResumeAnalysisService
from services.ai.service import AIService
from services.ai.settings import AISettings
from domain.resume_analysis import AnalysisRequest

NEW={'resume_analysis_reports','resume_analysis_decisions','resume_analysis_review_events'}

def test_additive_0016_roundtrip_and_existing_user_survives(tmp_path):
    url=f'sqlite:///{tmp_path}/migration.db';upgrade_database(url,'20260914_0015');db=create_database(url)
    old=set(inspect(db.engine).get_table_names());uid=str(uuid4())
    with db.session() as s,s.begin():s.add(User(id=uid,status='active',email_verified_at=1,created_at=1,updated_at=1))
    upgrade_database(url,'20260915_0016');assert current_revision(db.engine)=='20260915_0016'
    assert set(inspect(db.engine).get_table_names())-old==NEW
    from alembic import command
    # Metadata includes successor tables: check HEAD, then keep this test
    # focused on the historical 0016 round trip.
    upgrade_database(url)
    command.check(alembic_config(url))
    downgrade_database(url,'20260915_0016')
    upgrade_database(url,'20260915_0016');downgrade_database(url,'20260914_0015')
    assert set(inspect(db.engine).get_table_names())==old
    with db.session() as s:assert s.get(User,uid)
    upgrade_database(url,'20260915_0016');assert current_revision(db.engine)=='20260915_0016';db.dispose()

@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'),reason='Disposable PostgreSQL CI database required')
def test_postgresql_reports_persist_and_parallel_save_is_unique():
    from concurrent.futures import ThreadPoolExecutor
    url=os.environ['POSTGRES_TEST_URL'];upgrade_database(url);db=create_database(url);uid=str(uuid4());now=int(time.time())
    with db.session() as s,s.begin():s.add(User(id=uid,status='active',email_verified_at=now,created_at=now,updated_at=now))
    try:
        svc=ResumeAnalysisService(ResumeAnalysisRepository(db),AIService(AIRepository(db),AISettings(),fingerprint_key='test'),fingerprint_key='test')
        fid='resume-analysis-en-01';req=AnalysisRequest(uid,str(uuid4()),fid,svc.source(fid)[2])
        with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(lambda _:svc.create_reference(req),range(3)))
        assert all(r.report for r in results) and len({r.report['id'] for r in results})==1
        rid=results[0].report['id'];db.dispose()
        assert svc.get(uid,rid)['origin']=='reference'
        assert NEW<=set(inspect(db.engine).get_table_names())
    finally:
        with db.session() as s,s.begin():s.execute(delete(User).where(User.id==uid))
        db.dispose()
