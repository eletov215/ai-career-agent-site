"""Additive 0017 and mandatory disposable PostgreSQL CI scenarios."""
from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, inspect, select
from database import CURRENT_REVISION, alembic_config, create_database, current_revision, downgrade_database, upgrade_database
from models import User, ResumeDraft, ResumeVersion
from domain.resume_interview import StartInterviewRequest, InterviewCommand, InterviewError
from repositories.resume_interview import ResumeInterviewRepository
from services.resume_interview import ResumeInterviewService
from tests.test_ai003_service import start, review, confirm_command

NEW_TABLES = {'resume_interview_sessions', 'resume_interview_events'}


def test_0017_round_trip_preserves_existing_data_and_confirmed_resume(tmp_path):
    from alembic import command
    url = f'sqlite:///{tmp_path}/migration.db'
    upgrade_database(url, '20260915_0016')
    db = create_database(url)
    old = set(inspect(db.engine).get_table_names())
    owner = str(uuid4())
    with db.session() as session, session.begin():
        session.add(User(id=owner, status='active', email_verified_at=1, created_at=1, updated_at=1))
    upgrade_database(url)
    assert CURRENT_REVISION == current_revision(db.engine) == '20260916_0017'
    assert set(inspect(db.engine).get_table_names()) - old == NEW_TABLES
    command.check(alembic_config(url))
    svc = ResumeInterviewService(ResumeInterviewRepository(db), fingerprint_key='test')
    env = (db, owner, '', svc)
    result = review(env)
    final = svc.execute(confirm_command(env, result))
    upgrade_database(url)  # Idempotent.
    downgrade_database(url, '20260915_0016')
    assert set(inspect(db.engine).get_table_names()) == old
    with db.session() as session:
        assert session.get(User, owner)
        draft = session.get(ResumeDraft, result['draft_id'])
        assert draft.revision == 2
        assert session.get(ResumeVersion, final['confirmed_version_id'])
    upgrade_database(url)
    command.check(alembic_config(url))
    assert not svc.history(owner)  # Downgrade deliberately removed interview history, not drafts.
    db.dispose()


@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'), reason='Disposable PostgreSQL service required in GitHub CI')
def test_postgresql_interview_ownership_parallelism_confirmation_and_persistence():
    url = os.environ['POSTGRES_TEST_URL']
    upgrade_database(url)
    db = create_database(url)
    owner, other = str(uuid4()), str(uuid4())
    with db.session() as session, session.begin():
        for uid in (owner, other):
            session.add(User(id=uid, status='active', email_verified_at=1, created_at=1, updated_at=1))
    svc = ResumeInterviewService(ResumeInterviewRepository(db), fingerprint_key='test')
    env = (db, owner, other, svc)
    try:
        key = str(uuid4())
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda _: start(env, key=key), range(3)))
        assert len({r['id'] for r in results}) == 1
        result = review(env)
        cmd = confirm_command(env, result)
        with ThreadPoolExecutor(max_workers=3) as pool:
            outputs = list(pool.map(lambda _: svc.execute(cmd), range(3)))
        assert len({r['confirmed_version_id'] for r in outputs}) == 1
        db.dispose()
        assert svc.get(owner, result['id'])['status'] == 'confirmed'
        with pytest.raises(InterviewError, match='not_found'):
            svc.get(other, result['id'])
        assert NEW_TABLES <= set(inspect(db.engine).get_table_names())
    finally:
        with db.session() as session, session.begin():
            session.execute(delete(User).where(User.id.in_([owner, other])))
        db.dispose()
