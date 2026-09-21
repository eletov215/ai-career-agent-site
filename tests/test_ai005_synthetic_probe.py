import json
from pathlib import Path
import pytest
from scripts.ai005_synthetic_probe import execute,seed
from services.ai.letter_admission import synthetic_cases,SyntheticLetterAdmission
from services.ai.letter_contract import build_writing_contract
from tests.test_job001_service import job_env


def test_preview_cannot_contact_provider(tmp_path):
    def forbidden(*args,**kwargs):raise AssertionError('No provider construction for preview')
    out=tmp_path/'preview'
    r=execute(out,environ={},provider_factory=forbidden)
    assert r['network_calls']==0
    assert json.loads((out/'request-preview.json').read_text())['scope']=='synthetic_only'
    with pytest.raises(FileExistsError):execute(out,environ={})


@pytest.mark.parametrize('key',['DATABASE_URL','POSTGRES_TEST_URL','RESTORE_DATABASE_URL','RENDER','RENDER_SERVICE_ID'])
def test_production_shell_rejected(tmp_path,key):
    with pytest.raises(ValueError):execute(tmp_path/'out',environ={key:'private-not-printed'})


def test_paid_gate_not_bypassed_by_command(tmp_path):
    with pytest.raises(ValueError):execute(tmp_path/'out',allow_billable=True,environ={})
    assert not (tmp_path/'out'/'proposal-for-review.json').exists()


@pytest.mark.parametrize('language',['ru','en'])
def test_seed_matches_exact_pinned_manifest_and_no_application_import(job_env,language):
    uid,svc,saved_id,s,key=seed(job_env.db,synthetic_cases()[language],1789905600)
    c=build_writing_contract(s['source'],['profile.summary'],language,'short','professional')
    assert SyntheticLetterAdmission(uid).check(user_id=uid,letter_id='isolated',contract=c,now=1)=='synthetic-test-only-v1'


def test_complete_probe_uses_real_adapter_with_fake_transport_only(tmp_path,monkeypatch):
    from datetime import datetime,timezone,date
    import time
    from services.ai.provider import YandexAliceProvider
    from services.ai.policy import DEFAULT_POLICY
    from tests.test_ai005_live_runtime import StubTransport
    # Current date here is fixture setup, not new rate verification evidence.
    monkeypatch.setitem(DEFAULT_POLICY,'pricing_checked_on',date.today().isoformat())
    transport=StubTransport()
    env={'AI_ENABLED':'1','AI_KILL_SWITCH':'0','AI_SYNTHETIC_ACCESS_ENABLED':'1',
         'AI_YANDEX_API_KEY':'test-only','AI_YANDEX_FOLDER_ID':'fixture-folder',
         'AI_YANDEX_MODEL_URI':'gpt://fixture-folder/aliceai-llm/latest',
         'AI_NO_LOGGING_DISABLED_AT':datetime.fromtimestamp(time.time()-90000,timezone.utc).isoformat()}
    out=tmp_path/'run'
    r=execute(out,language='en',allow_billable=True,environ=env,
        provider_factory=lambda settings:YandexAliceProvider(settings,transport=transport))
    assert r['dispatches']==1 and len(transport.calls)==1
    assert r['status']=='proposal' and r['real_data_authorized'] is False
    assert (out/'proposal-for-review.json').is_file()
    report=json.loads((out/'report.json').read_text())
    assert report['live_quality']=='REQUIRES_HUMAN_REVIEW'
    assert 'fixture-folder' not in json.dumps(report)
