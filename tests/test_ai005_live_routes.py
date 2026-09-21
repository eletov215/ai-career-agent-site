"""Installed-CI native HTTP generation controls. No external calls."""
import html
import re
from types import SimpleNamespace
import pytest
pytest.importorskip('flask',reason='Pinned Flask required; skipped is not HTTP verification')
from werkzeug.datastructures import MultiDict
from tests.test_ai005_routes import web,csrf
from tests.test_ai005_live_runtime import live
from tests.test_ai005_service import letters
from tests.test_job001_service import job_env


def prepare(web,live):
    # Both fixtures share the same owner/disposable database.
    web.e.svc.generator=live.generator
    return '/cover-letters/'+live.record['id']


def form(web,live):
    return {'csrf_token':csrf(web.client),'expected_revision':str(live.record['revision']),
            'language':'en','length':'short','tone':'professional','fact_id':'profile.summary'}


def test_preview_native_confirmation_and_duplicate_generation(web,live):
    path=prepare(web,live);c=web.client
    response=c.post(path+'/generation-preview',data=form(web,live))
    assert response.status_code==200 and 'no-store' in response.headers['Cache-Control']
    body=response.get_data(as_text=True)
    assert 'Built REST API tests' in body and 'private@example.test' not in body
    token=html.unescape(re.search(r'name="review_token" value="([^"]+)"',body).group(1))
    data={'csrf_token':csrf(c),'review_token':token,'confirm':'1'}
    bad=c.post(path+'/generate',data={**data,'confirm':'0'})
    assert bad.status_code==400 and not live.transport.calls
    good=c.post(path+'/generate',data=data)
    assert good.status_code==303 and '?proposal=' in good.location
    page=c.get(good.location);assert page.status_code==200
    assert 'alice_draft' not in page.get_data(as_text=True)  # A translated UI label.
    again=c.post(path+'/generate',data=data)
    assert again.location==good.location and len(live.transport.calls)==1


def test_generation_strict_forms_csrf_ownership_and_default_closed(web,live):
    path=prepare(web,live);c=web.client;valid=form(web,live)
    assert c.post(path+'/generation-preview',data={k:v for k,v in valid.items() if k!='csrf_token'}).status_code==400
    assert c.post(path+'/generation-preview',data={**valid,'user_id':web.e.other}).status_code==400
    multi=MultiDict(valid);multi.add('language','ru')
    assert c.post(path+'/generation-preview',data=multi).status_code==400
    assert c.post(path+'/generation-preview',json=valid,headers={'X-CSRFToken':valid['csrf_token']}).status_code==400
    web.identity.user.id=web.e.other
    assert c.post(path+'/generation-preview',data=form(web,live)).status_code==404
    assert c.post(path+'/generate',data={'csrf_token':csrf(c),'confirm':'1','review_token':live.preview['review_token']}).status_code==404
    web.identity.user=None
    assert c.post(path+'/generate',data={'csrf_token':valid['csrf_token']},headers={'Accept':'application/json'}).status_code==401
    assert not live.transport.calls


def test_default_application_stays_closed_when_unrelated_flags_enabled(client,app_module,monkeypatch):
    from services.ai.letter_admission import ClosedLetterAdmission
    assert isinstance(app_module.COVER_LETTER_GENERATOR.admission,ClosedLetterAdmission)
    monkeypatch.setenv('AI_ENABLED','1');monkeypatch.setenv('AI_SYNTHETIC_ACCESS_ENABLED','1')
    assert isinstance(app_module.COVER_LETTER_GENERATOR.admission,ClosedLetterAdmission)
    assert app_module.AI_SERVICE.public_status()['generation_available'] is False
