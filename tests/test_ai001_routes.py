from pathlib import Path
import json
import pytest
ROOT=Path(__file__).resolve().parents[1]

def test_status_get_is_safe_no_store_and_never_calls_provider(client,app_module,monkeypatch):
    def forbidden(*a,**k):raise AssertionError('No provider call on status')
    monkeypatch.setattr(app_module.AI_SERVICE.provider,'generate',forbidden)
    response=client.get('/api/ai/status')
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    data=response.get_json();assert not data['generation_available'] and data['mode']=='manual'
    for key in ('api_key','model_uri','user_id','folder_id'):assert key not in data
    rules=list(app_module.app.url_map.iter_rules())
    assert all(not ('POST' in r.methods) for r in rules if str(r).startswith('/api/ai/'))

def test_manual_mode_notice_is_rendered(client):
    res=client.get('/ai-career');assert res.status_code==200
    assert 'ai-manual-notice' in res.get_data(as_text=True)

def test_templates_use_server_rendered_notice_and_preserve_editor():
    for file in ('ai_career.html','resume_builder.html'):
        assert 'partials/ai_manual_notice.html' in (ROOT/'templates'/file).read_text()
    t=(ROOT/'templates/partials/ai_manual_notice.html').read_text()
    assert 'role="status"' in t and 'aria-live="polite"' in t
    assert '|safe' not in t

def test_privacy_export_includes_only_owner_usage_metadata(tmp_path):
    from uuid import uuid4
    from database import create_database,upgrade_database
    from models import User
    from models.ai import AIUsageEvent
    from repositories.privacy import PrivacyRepository
    from repositories.ai import AIRepository
    from services.ai.registry import ContractRegistry
    import time
    url=f'sqlite:///{tmp_path}/export.db';upgrade_database(url);db=create_database(url);now=int(time.time())
    user=str(uuid4());other=str(uuid4())
    with db.session() as s,s.begin():
        for uid in (user,other):s.add(User(id=uid,status='active',email_verified_at=now,password_hash='fixture-hash',created_at=now,updated_at=now))
    repo=AIRepository(db);v,p=repo.read_policy()
    repo.update_policy({'enabled':True,'kill_switch':False,'pricing_checked_on':time.strftime('%Y-%m-%d',time.gmtime(now))},expected_version=v,now=now)
    fixture,_=ContractRegistry().load('resume-analysis-en-01')
    for uid in (user,other):repo.admit(user_id=uid,key_hash='a'*64,request_hash='b'*64,fixture=fixture,now=now)
    snapshot,_=PrivacyRepository(db).export_snapshot(user,expected_password_hash='fixture-hash')
    assert len(snapshot['ai_usage'])==1
    assert 'idempotency_hash' not in json.dumps(snapshot['ai_usage']) and 'request_hash' not in json.dumps(snapshot['ai_usage'])
    counts=PrivacyRepository(db).delete_account(user,expected_password_hash='fixture-hash',now=now)
    assert counts['ai_usage_events']==1 and not repo.owner_usage(user) and len(repo.owner_usage(other))==1
    db.dispose()
