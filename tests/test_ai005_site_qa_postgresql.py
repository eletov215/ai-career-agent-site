"""Real PostgreSQL locking, mock provider, private disposable schema only."""
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import text, select, func
from sqlalchemy.engine import make_url

from database import create_database
from models.cover_letter import CoverLetter, CoverLetterProposal
from models.ai import AIUsageEvent
from models import User
from tests.site_qa_support import build_case


@pytest.mark.skipif(not os.environ.get('POSTGRES_TEST_URL'), reason='Disposable PostgreSQL required')
def test_site_qa_postgresql_creation_dispatch_and_actor_revocation(tmp_path):
    assert os.environ.get('APP_ENV') == 'test'
    url = os.environ['POSTGRES_TEST_URL']
    admin = create_database(url)
    schema = 'siteqa_' + uuid4().hex
    case = None
    try:
        with admin.engine.begin() as c:
            c.execute(text('CREATE SCHEMA ' + schema))
        scoped = make_url(url).update_query_dict({'options': '-csearch_path=' + schema}).render_as_string(hide_password=False)
        case = build_case(tmp_path, url=scoped)
        qa = case.qa
        intent = qa.new_intention(case.admin)
        with ThreadPoolExecutor(max_workers=2) as pool:
            letters = list(pool.map(lambda _: qa.prepare(case.admin, intent, 'en', 'short', 'professional'), range(2)))
        assert letters[0] == letters[1]
        lid = letters[0]
        preview = qa.preview(case.admin, lid)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: qa.generate(case.admin, lid, preview['review_token']), range(2)))
        assert len(case.transport.calls) == 1 and any(r['status'] == 'proposal' for r in results)
        with case.db.session() as s:
            assert s.scalar(select(func.count()).select_from(CoverLetter)) == 1
            assert s.scalar(select(func.count()).select_from(CoverLetterProposal)) == 1
            assert s.scalar(select(AIUsageEvent)).attempts == 1
            assert s.scalar(text('SELECT count(*) FROM ai_consents')) == 0
        lid2 = qa.prepare(case.admin, qa.new_intention(case.admin), 'en', 'short', 'professional')
        preview2 = qa.preview(case.admin, lid2)
        def revoke():
            with case.db.session() as s, s.begin():
                s.get(User, case.admin).status = 'disabled'
        case.transport.before = revoke
        result = qa.generate(case.admin, lid2, preview2['review_token'])
        assert result['status'] == 'manual' and result['reason'] == 'result_not_delivered'
        with case.db.session() as s:
            assert sorted(s.scalars(select(AIUsageEvent.status))) == ['failed', 'succeeded']
            assert s.scalar(select(func.count()).select_from(CoverLetterProposal)) == 1
    finally:
        if case:
            case.db.dispose()
        with admin.engine.begin() as c:
            c.execute(text('DROP SCHEMA IF EXISTS ' + schema + ' CASCADE'))
        admin.dispose()
