"""Real PostgreSQL r2 ledger/proposal transaction; disposable isolated schema."""
import os
import secrets
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import text,select,func
from sqlalchemy.engine import make_url
from database import create_database,upgrade_database
from services.ai.settings import AISettings
from services.ai.service import AIService
from services.ai.provider import YandexAliceProvider
from services.ai.letter_runtime import LetterRuntime
from services.ai.letter_admission import SyntheticLetterAdmission,synthetic_cases
from services.cover_letter_ai import CoverLetterGenerator
from repositories.ai import AIRepository
from models.ai import AIUsageEvent
from models.cover_letter import CoverLetterProposal
from scripts.ai005_synthetic_probe import seed
from tests.test_ai005_live_runtime import StubTransport


@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'),reason='Isolated disposable PostgreSQL required for r2 atomic delivery')
def test_postgresql_atomic_delivery_replay_and_stale_result():
    url=os.environ['POSTGRES_TEST_URL'];admin=create_database(url)
    schema='ai005r2_'+uuid4().hex;db=None
    try:
        with admin.engine.begin() as c:c.execute(text('CREATE SCHEMA '+schema))
        scoped=make_url(url).update_query_dict({'options':'-csearch_path='+schema}).render_as_string(hide_password=False)
        upgrade_database(scoped);db=create_database(scoped);now=int(time.time())
        uid,svc,saved,source,key=seed(db,synthetic_cases()['en'],now)
        row=svc.create(uid,saved,source['source_hash'],uuid4().hex,'en','short','professional',confirmed=True)
        ledger=AIRepository(db);version,_=ledger.read_policy()
        ledger.update_policy({'enabled':True,'kill_switch':False,'pricing_checked_on':date.today().isoformat()},expected_version=version,now=now)
        settings=AISettings(True,False,True,'test-only','fixture-folder','gpt://fixture-folder/aliceai-llm/latest',now-90000)
        transport=StubTransport();ai=AIService(ledger,settings,fingerprint_key=key,provider=YandexAliceProvider(settings,transport=transport))
        gen=CoverLetterGenerator(svc.repository,LetterRuntime(ai),signing_key=key,admission=SyntheticLetterAdmission(uid))
        preview=gen.preview(uid,row['id'],1,'en','short','professional',['profile.summary'])
        def call(_):return gen.generate(uid,row['id'],preview['review_token'],confirmed=True)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(call,range(2)))
        assert len(transport.calls)==1 and any(r['status']=='proposal' for r in results)
        with db.session() as s:
            assert s.scalar(select(func.count()).select_from(CoverLetterProposal))==1
            event=s.scalar(select(AIUsageEvent));assert event.status=='succeeded' and event.attempts==1
        # New deliberate operation, then change the manual letter during I/O.
        next_preview=gen.preview(uid,row['id'],1,'en','short','professional',['profile.summary'])
        def edit():svc.save(uid,row['id'],1,'Manual','Human edit wins.','en','short','professional',confirmed=True)
        transport.before=edit
        result=gen.generate(uid,row['id'],next_preview['review_token'],confirmed=True)
        assert result['status']=='manual' and result['reason']=='result_not_delivered'
        with db.session() as s:
            statuses=list(s.scalars(select(AIUsageEvent.status)))
            assert sorted(statuses)==['failed','succeeded']
            assert s.scalar(select(func.count()).select_from(CoverLetterProposal))==1
        assert svc.get(uid,row['id'])['content']['body']=='Human edit wins.'
    finally:
        if db:db.dispose()
        with admin.engine.begin() as c:c.execute(text('DROP SCHEMA IF EXISTS '+schema+' CASCADE'))
        admin.dispose()
