"""Mandatory installed-CI HTTP tests: native forms, CSRF and owner/session gates."""
from types import SimpleNamespace
from uuid import uuid4
from io import BytesIO
import html
import re
import pytest
pytest.importorskip('flask',reason='Flask HTTP tests require installed application dependencies in CI')
from flask import Flask,g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader,DictLoader,FileSystemLoader
from werkzeug.datastructures import MultiDict
from routes.vacancy_match import create_vacancy_match_blueprint,_REVIEW_SESSION_KEY
from services.vacancy_match import ROOT
from tests.test_ai004_service import env,req

@pytest.fixture
def web(env):
    user=SimpleNamespace(id=env[1],status='active',email_verified_at=1,normalized_email='admin@example.invalid')
    settings=SimpleNamespace(search_admin_emails=('admin@example.invalid',))
    app=Flask(__name__);app.config.update(TESTING=True,SECRET_KEY='test-only')
    CSRFProtect(app)
    @app.before_request
    def identity():g.current_user=user
    app.register_blueprint(create_vacancy_match_blueprint(env[-1],settings))
    app.jinja_loader=ChoiceLoader([DictLoader({'base.html':'<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),FileSystemLoader(ROOT/'templates')])
    return app.test_client(),user,env


def csrf(response):
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"',response.get_data(as_text=True)).group(1))


def unlock(client):
    gate=client.get('/ai-match/review');assert gate.status_code==200
    token=csrf(gate)
    assert client.post('/ai-match/review/enable',data={'csrf_token':token}).status_code==303
    return token


def form(env,token):
    r=req(env)
    return {'csrf_token':token,'fixture_id':r.fixture_id,'source_hash':r.source_hash,'operation_key':r.operation_key}


def test_admin_session_unlock_disable_and_no_shared_interview_unlock(web):
    client,user,env=web
    assert client.get('/ai-match').status_code==404
    with client.session_transaction() as session:session['ai003_review_enabled']=True
    assert client.get('/ai-match').status_code==404
    token=unlock(client)
    assert client.get('/ai-match').status_code==200
    assert client.post('/ai-match/review/disable',data={'csrf_token':token}).status_code==303
    assert client.get('/ai-match').status_code==404
    unlock(client)
    with client.session_transaction() as session:session.clear()
    assert client.get('/ai-match').status_code==404


@pytest.mark.parametrize('attr,value',[('normalized_email','other@example.invalid'),('status','pending'),('email_verified_at',None)])
def test_gate_and_all_read_paths_remain_hidden_from_nonadmins(web,attr,value):
    client,user,env=web;token=unlock(client);report=env[-1].create_reference(req(env))
    setattr(user,attr,value)
    for path in ('/ai-match/review','/ai-match',f"/ai-match/{report['id']}",f"/api/vacancy-matches/{report['id']}"):
        assert client.get(path).status_code==404
    assert client.post('/ai-match/review/enable',data={'csrf_token':token}).status_code==404


def test_reference_forms_persist_show_safe_score_and_require_delete_confirmation(web,monkeypatch):
    client,user,env=web;token=unlock(client)
    def forbidden(*args,**kwargs):raise AssertionError('No paid UI call')
    monkeypatch.setattr(env[-1].runtime,'generate',forbidden)
    data=form(env,token);result=client.post('/ai-match/reference',data=data)
    assert result.status_code==303
    again=client.post('/ai-match/reference',data=data)
    assert again.location==result.location
    page=client.get(result.location)
    assert page.status_code==200 and page.headers['X-Robots-Tag']=='noindex, nofollow'
    assert 'no-store' in page.headers['Cache-Control'] and 'ETag' not in page.headers
    text=page.get_data(as_text=True)
    assert 'data-mandatory-warning' in text and 'Docker' in text and '67' in text
    report=env[-1].history(user.id)[0]
    api=client.get(f"/api/vacancy-matches/{report['id']}")
    assert api.json['report']['result']['summary']['score_percent']==67
    assert 'operation_hash' not in api.get_data(as_text=True)
    path=f"/ai-match/{report['id']}/delete"
    assert client.post(path,data={'csrf_token':token,'result_hash':report['result_hash']}).status_code==400
    assert client.post(path,data={'csrf_token':token,'result_hash':'0'*64,'confirm':'1'}).status_code==409
    assert client.post(path,data={'csrf_token':token,'result_hash':report['result_hash'],'confirm':'1'}).status_code==303
    assert client.get(result.location).status_code==404


def test_all_post_controls_require_csrf_and_reject_arbitrary_data(web):
    client,user,env=web
    assert client.post('/ai-match/review/enable',data={}).status_code==400
    token=unlock(client);data=form(env,token)
    assert client.post('/ai-match/reference',data={k:v for k,v in data.items() if k!='csrf_token'}).status_code==400
    for extra in ({'resume':'private text'},{'vacancy_url':'https://example.invalid'},{'score':'100'},{'profile_id':user.id}):
        assert client.post('/ai-match/reference',data={**data,**extra}).status_code==400
    duplicated=MultiDict(data);duplicated.add('fixture_id',data['fixture_id'])
    assert client.post('/ai-match/reference',data=duplicated).status_code==400
    assert client.post('/ai-match/reference',json=data,headers={'X-CSRF-Token':token}).status_code==400
    assert client.post('/ai-match/reference',data={**data,'file':(BytesIO(b'secret'),'cv.pdf')}).status_code==400
    assert client.post('/ai-match/review/enable',data={'csrf_token':token,'unexpected':'text'}).status_code==400
    assert not env[-1].history(user.id)


def test_different_allowlisted_admin_cannot_read_or_delete_other_reports(web):
    client,user,env=web;token=unlock(client);report=env[-1].create_reference(req(env))
    user.id=env[2]
    # An unlock is bound to a user, not just a generic true bit.
    assert client.get('/ai-match').status_code==404
    token=unlock(client)
    assert client.get(f"/ai-match/{report['id']}").status_code==404
    assert client.get(f"/api/vacancy-matches/{report['id']}").status_code==404
    assert client.post(f"/ai-match/{report['id']}/delete",data={'csrf_token':token,'result_hash':report['result_hash'],'confirm':'1'}).status_code==404


def test_stale_source_and_storage_errors_are_safe(web,monkeypatch):
    from sqlalchemy.exc import OperationalError
    client,user,env=web;token=unlock(client);data=form(env,token)
    response=client.post('/ai-match/reference',data={**data,'source_hash':'0'*64})
    assert response.status_code==409
    def fail(*args,**kwargs):raise OperationalError('secret SQL',{'password':'do-not-show'},RuntimeError('secret'))
    monkeypatch.setattr(env[-1],'create_reference',fail)
    response=client.post('/ai-match/reference',data=data)
    assert response.status_code==503 and 'do-not-show' not in response.get_data(as_text=True)


def test_real_application_registration_closed_status_and_no_browser_provider_post(client,app_module):
    assert client.get('/ai-match').status_code==404
    assert client.get('/ai-match/review').status_code==404
    status=client.get('/api/ai/status')
    assert status.json['generation_available'] is False and status.json['mode']=='manual'
    rules={str(rule) for rule in app_module.app.url_map.iter_rules()}
    assert '/ai-match/<uuid:report_id>' in rules
    assert '/api/vacancy-matches/<uuid:report_id>' in rules
