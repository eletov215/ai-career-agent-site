"""Installed-CI Flask HTTP tests. An absent Flask module is an explicit skip."""
import html
import json
import re
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
pytest.importorskip('flask', reason='Install pinned Flask dependencies for JOB-001 HTTP tests')
from flask import Flask, g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from sqlalchemy.exc import OperationalError
from werkzeug.datastructures import MultiDict
from routes.saved_vacancies import create_saved_vacancies_blueprint
from tests.test_job001_service import job_env, payload, reference, add_search

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def web(job_env):
    e=job_env;identity=SimpleNamespace(user=SimpleNamespace(id=e.owner,status='active',email_verified_at=1))
    app=Flask(__name__);app.config.update(TESTING=True,SECRET_KEY='job001-http-test')
    CSRFProtect(app)
    @app.before_request
    def bind_user():g.current_user=identity.user
    app.add_url_rule('/auth/login', endpoint='auth.login', view_func=lambda:'Login')
    app.add_url_rule('/vacancies', endpoint='vacancies', view_func=lambda:'Search')
    app.register_blueprint(create_saved_vacancies_blueprint(e.svc))
    app.jinja_loader=ChoiceLoader([DictLoader({'base.html':'<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),FileSystemLoader(ROOT/'templates')])
    return SimpleNamespace(client=app.test_client(),identity=identity,env=e)


def csrf(client):
    page=client.get('/saved-vacancies')
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"',page.get_data(as_text=True)).group(1))


def create(web):
    token,_,_=reference(web.env)
    return web.client.post('/saved-vacancies/save',data={'csrf_token':csrf(web.client),'reference':token})


def test_native_save_detail_api_notes_delete_and_confirm(web):
    c=web.client;response=create(web);assert response.status_code==303
    location=response.location;id=location.rsplit('/',1)[1]
    page=c.get(location);assert page.status_code==200
    assert 'no-store' in page.headers['Cache-Control'] and page.headers['X-Robots-Tag']=='noindex, nofollow'
    assert 'Python Developer' in page.get_data(as_text=True)
    api=c.get('/api/saved-vacancies/'+id);assert api.json['vacancy']['snapshot']['title']=='Python Developer'
    token=csrf(c)
    note=c.post(location+'/note',data={'csrf_token':token,'note':'Personal note','expected_revision':'1'})
    assert note.status_code==303
    assert c.get(location).get_data(as_text=True).count('Personal note')==1
    assert c.post(location+'/delete',data={'csrf_token':token,'expected_revision':'2'}).status_code==400
    assert c.post(location+'/delete',data={'csrf_token':token,'expected_revision':'1','confirm':'1'}).status_code==409
    assert c.post(location+'/delete',data={'csrf_token':token,'expected_revision':'2','confirm':'1'}).status_code==303
    assert c.get(location).status_code==404 and c.get('/api/saved-vacancies/'+id).status_code==404


def test_ajax_replay_returns_same_id_and_no_extra_row(web):
    c=web.client;t,_,_=reference(web.env);data={'csrf_token':csrf(c),'reference':t};headers={'Accept':'application/json'}
    first=c.post('/saved-vacancies/save',data=data,headers=headers)
    second=c.post('/saved-vacancies/save',data=data,headers=headers)
    assert first.status_code==201 and second.status_code==200
    assert first.json['id']==second.json['id']
    assert second.json['created'] is False


def test_all_posts_require_csrf_and_reject_extra_duplicate_json_and_uploads(web):
    c=web.client;t,_,_=reference(web.env)
    assert c.post('/saved-vacancies/save',data={'reference':t}).status_code==400
    token=csrf(c);base={'csrf_token':token,'reference':t}
    for extra in ({'user_id':web.env.other},{'description':'invented'},{'url':'https://evil.invalid'},{'score':'100'}):
        assert c.post('/saved-vacancies/save',data={**base,**extra}).status_code==400
    multi=MultiDict(base);multi.add('reference',t)
    assert c.post('/saved-vacancies/save',data=multi).status_code==400
    assert c.post('/saved-vacancies/save',json=base,headers={'X-CSRF-Token':token}).status_code==400
    assert c.post('/saved-vacancies/save',data={**base,'file':(BytesIO(b'data'),'resume.pdf')}).status_code==400
    assert web.env.svc.list(web.env.owner)['total']==0


def test_cross_owner_reads_notes_deletion_and_reference_fail(web):
    c=web.client;response=create(web);loc=response.location;id=loc.rsplit('/',1)[1]
    t,_,_=reference(web.env);web.identity.user.id=web.env.other;token=csrf(c)
    assert c.get(loc).status_code==404
    assert c.get('/api/saved-vacancies/'+id).status_code==404
    assert c.post(loc+'/note',data={'csrf_token':token,'note':'attack','expected_revision':'1'}).status_code==404
    assert c.post(loc+'/delete',data={'csrf_token':token,'confirm':'1','expected_revision':'1'}).status_code==404
    assert c.post('/saved-vacancies/save',data={'csrf_token':token,'reference':t}).status_code==409


def test_logged_out_and_unverified_access_is_denied(web):
    web.identity.user=None
    assert web.client.get('/saved-vacancies').status_code==302
    assert web.client.get('/api/saved-vacancies/'+str(uuid4())).status_code==401
    web.identity.user=SimpleNamespace(id=web.env.owner,status='active',email_verified_at=None)
    assert web.client.get('/saved-vacancies').status_code==404


def test_stale_note_shows_both_versions_escaped_without_resubmit(web):
    c=web.client;response=create(web);loc=response.location;token=csrf(c)
    assert c.post(loc+'/note',data={'csrf_token':token,'note':'Server note','expected_revision':'1'}).status_code==303
    conflict=c.post(loc+'/note',data={'csrf_token':token,'note':'<script>unsaved</script>','expected_revision':'1'})
    assert conflict.status_code==409
    body=conflict.get_data(as_text=True)
    assert 'Server note' in body and '&lt;script&gt;unsaved&lt;/script&gt;' in body
    assert '<script>unsaved' not in body and 'name="expected_revision"' not in body


def test_legacy_needs_explicit_confirmation_and_is_partial(web):
    c=web.client;token=csrf(c);raw=payload();add_search(web.env.db,raw)
    assert c.post('/saved-vacancies/import-legacy',data={'csrf_token':token,'keys':json.dumps([raw['url']])}).status_code==400
    answer=c.post('/saved-vacancies/import-legacy',data={'csrf_token':token,'confirm':'1','keys':json.dumps([raw['url'],'missing'])})
    assert answer.status_code==200 and answer.json['saved_count']==1 and answer.json['unresolved_count']==1


def test_safe_storage_errors_do_not_echo_sql_or_credentials(web,monkeypatch):
    def fail(*args,**kwargs):raise OperationalError('SELECT secret',{},Exception('postgresql://user:password@server'))
    monkeypatch.setattr(web.env.svc,'list',fail)
    result=web.client.get('/saved-vacancies');assert result.status_code==503
    text=result.get_data(as_text=True)
    assert 'SELECT secret' not in text and 'password' not in text


def test_real_application_login_search_save_relogin(client,app_module,monkeypatch):
    # Exercise the real app, real auth/session binding, real search aggregation and native template.
    from tests.test_resume_draft_routes import _register_verify_login, _login, _csrf
    from services.base_provider import SearchResult
    email='job001-'+uuid4().hex+'@example.test'
    _register_verify_login(app_module,client,email=email,next_path='/saved-vacancies')
    raw=payload()
    from datetime import datetime,timezone
    raw['published_at']=datetime.now(timezone.utc).isoformat()
    class Provider:
        def search(self, **kwargs):return SearchResult(items=[raw],total=1,page=0,pages=1,has_next=False)
    # Existing route factory chooses HH only when configured; test setup enables its mock.
    monkeypatch.setattr(app_module, 'HH_APP_TOKEN', 'test-token-not-live')
    monkeypatch.setattr(app_module, 'HeadHunterProvider', lambda *args,**kwargs:Provider())
    page=client.get('/vacancies?search=1&keyword=Python&source=hh')
    assert page.status_code==200
    text=page.get_data(as_text=True)
    found=re.search(r'name="reference" value="([^"]+)"',text)
    assert found, text[:3000]
    response=client.post('/saved-vacancies/save',data={'csrf_token':_csrf(page),'reference':html.unescape(found.group(1))})
    assert response.status_code==303
    location=response.location
    logout=client.post('/auth/logout',data={'csrf_token':_csrf(client.get('/'))})
    assert logout.status_code in (302,303)
    assert client.get(location).status_code==302
    _login(client,email=email,next_path='/saved-vacancies')
    assert client.get(location).status_code==200
    assert 'Python Developer' in client.get('/saved-vacancies').get_data(as_text=True)
