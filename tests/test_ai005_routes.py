"""Installed-CI HTTP/CSRF tests. Missing Flask is not a successful route test."""
import html
import re
from types import SimpleNamespace
from uuid import uuid4
from io import BytesIO
from pathlib import Path
import pytest
pytest.importorskip('flask',reason='Pinned Flask dependencies required for AI-005 HTTP verification')
from flask import Flask,g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader,DictLoader,FileSystemLoader
from werkzeug.datastructures import MultiDict
from sqlalchemy.exc import OperationalError
from routes.cover_letters import create_cover_letters_blueprint
from routes.saved_vacancies import create_saved_vacancies_blueprint
from tests.test_ai005_service import letters,new,save,proposal
from tests.test_job001_service import job_env

@pytest.fixture
def web(letters):
    e=letters;identity=SimpleNamespace(user=SimpleNamespace(id=e.owner,status='active',email_verified_at=1))
    app=Flask(__name__);app.config.update(TESTING=True,SECRET_KEY='ai005-test-only')
    CSRFProtect(app)
    @app.before_request
    def bind():g.current_user=identity.user
    app.add_url_rule('/auth/login',endpoint='auth.login',view_func=lambda:'Login')
    app.add_url_rule('/vacancies',endpoint='vacancies',view_func=lambda:'Search')
    app.register_blueprint(create_saved_vacancies_blueprint(e.env.svc))
    app.register_blueprint(create_cover_letters_blueprint(e.svc))
    app.jinja_loader=ChoiceLoader([DictLoader({'base.html':'<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),FileSystemLoader(Path(__file__).resolve().parents[1]/'templates')])
    return SimpleNamespace(client=app.test_client(),identity=identity,e=e)


def csrf(c):
    raw=c.get('/cover-letters').get_data(as_text=True)
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"',raw).group(1))


def create(web):
    e=web.e;c=web.client
    return c.post('/cover-letters/new',data={'csrf_token':csrf(c),'saved_id':e.saved_id,
       'source_hash':e.svc.source(e.owner,e.saved_id)['source_hash'],'operation_key':uuid4().hex,
       'language':'en','length':'short','tone':'professional','confirm':'1'})


def save_form(c,**changes):
    result={'csrf_token':csrf(c),'expected_revision':'1','subject':'Application','body':'My reviewed text.',
            'language':'en','length':'short','tone':'professional','confirm':'1','proposal_id':''}
    result.update(changes);return result


def test_native_creation_editor_review_versions_download_and_delete(web):
    c=web.client;e=web.e
    assert c.get('/saved-vacancies/'+e.saved_id+'/letters').status_code==200
    response=create(web);assert response.status_code==303;path=response.location
    page=c.get(path);assert page.status_code==200
    assert 'no-store' in page.headers['Cache-Control'] and page.headers['X-Robots-Tag']=='noindex, nofollow'
    assert c.post(path+'/save',data=save_form(c,confirm='0')).status_code==400
    assert c.post(path+'/save',data=save_form(c)).status_code==303
    api=c.get('/api'+path);assert api.json['letter']['last_version']==1
    out=c.get(path+'/versions/1/export.txt');assert out.status_code==200
    assert 'attachment' in out.headers['Content-Disposition'] and out.data.decode('utf-8-sig').endswith('My reviewed text.\n')
    assert c.post(path+'/delete',data={'csrf_token':csrf(c),'expected_revision':'2'}).status_code==400
    assert c.post(path+'/delete',data={'csrf_token':csrf(c),'expected_revision':'1','confirm':'1'}).status_code==409
    assert c.post(path+'/delete',data={'csrf_token':csrf(c),'expected_revision':'2','confirm':'1'}).status_code==303
    assert c.get(path).status_code==404 and c.get('/api'+path).status_code==404
    assert c.get('/saved-vacancies/'+e.saved_id).status_code==200


def test_csrf_json_upload_and_unknown_fields_rejected(web):
    c=web.client;path=create(web).location;valid=save_form(c)
    assert c.post(path+'/save',data={k:v for k,v in valid.items() if k!='csrf_token'}).status_code==400
    for extra in ({'user_id':web.e.other},{'origin':'ai'},{'source_json':'{}'}):
        assert c.post(path+'/save',data={**valid,**extra}).status_code==400
    multi=MultiDict(valid);multi.add('body','Duplicate')
    assert c.post(path+'/save',data=multi).status_code==400
    assert c.post(path+'/save',json=valid,headers={'X-CSRFToken':valid['csrf_token']}).status_code==400
    assert c.post(path+'/save',data={**valid,'file':(BytesIO(b'x'),'file.txt')}).status_code==400


def test_foreign_account_isolation_including_compare_and_export(web):
    c=web.client;row=save(web.e,new(web.e));path='/cover-letters/'+row['id']
    web.identity.user.id=web.e.other
    for suffix in ('','/versions/1','/versions/1/export.txt','/compare?left=1&right=1'):
        assert c.get(path+suffix).status_code==404
    assert c.get('/api'+path).status_code==404
    assert c.post(path+'/save',data=save_form(c,expected_revision='2')).status_code==404
    assert c.post(path+'/delete',data={'csrf_token':csrf(c),'expected_revision':'2','confirm':'1'}).status_code==404


def test_logged_out_pages_redirect_api_401_unverified_404(web):
    c=web.client;path=create(web).location
    web.identity.user=None
    assert c.get(path).status_code==302 and c.get('/api'+path).status_code==401
    web.identity.user=SimpleNamespace(id=web.e.owner,status='active',email_verified_at=None)
    assert c.get('/cover-letters').status_code==404


def test_stale_editor_preserves_unsaved_text_without_fresh_revision_form(web):
    c=web.client;path=create(web).location
    assert c.post(path+'/save',data=save_form(c)).status_code==303
    reply=c.post(path+'/save',data=save_form(c,body='<script>unsaved</script>'))
    assert reply.status_code==409
    raw=reply.get_data(as_text=True)
    assert '&lt;script&gt;unsaved&lt;/script&gt;' in raw and '<script>unsaved' not in raw
    assert 'My reviewed text.' in raw and 'name="expected_revision"' not in raw


def test_local_proposal_confirmation_and_stale_discard(web):
    c=web.client;e=web.e;path=create(web).location
    form={'csrf_token':csrf(c),'expected_revision':'1','language':'en','length':'short',
          'tone':'professional','operation_key':uuid4().hex,'fact_id':['profile.summary','profile.skills.0.name']}
    response=c.post(path+'/compose',data=form);assert response.status_code==303
    assert c.get(response.location).status_code==200
    assert c.post(path+'/save',data=save_form(c)).status_code==303
    conflict=c.get(response.location);assert conflict.status_code==409
    # A stale pending proposal can still be discarded from the current document.
    pending=e.svc.get(e.owner,path.rsplit('/',1)[1])['proposals'][0]
    assert pending['id'] in c.get(path).get_data(as_text=True)
    discard=c.post(path+'/proposals/'+pending['id']+'/delete',data={'csrf_token':csrf(c),'expected_revision':'2','confirm':'1'})
    assert discard.status_code==303


def test_saved_vacancy_deletion_is_protected(web):
    c=web.client;path=create(web).location;saved=web.e.env.svc.get(web.e.owner,web.e.saved_id)
    response=c.post('/saved-vacancies/'+web.e.saved_id+'/delete',data={'csrf_token':csrf(c),'confirm':'1','expected_revision':saved['revision']})
    assert response.status_code==409 and c.get(path).status_code==200


def test_unavailable_generation_never_looks_successful(web):
    c=web.client;path=create(web).location
    response=c.post(path+'/generate',data={'csrf_token':csrf(c)},headers={'Accept':'application/json'})
    assert response.status_code==503 and response.json['ok'] is False
    assert response.json['code']=='generation_unavailable'


def test_storage_errors_are_neutral_and_no_user_content_echo(web,monkeypatch):
    def fail(*a,**k):raise OperationalError('SELECT secret',{},Exception('postgresql://user:password@host'))
    monkeypatch.setattr(web.e.svc,'list',fail)
    response=web.client.get('/cover-letters');assert response.status_code==503
    assert 'password' not in response.get_data(as_text=True) and 'SELECT' not in response.get_data(as_text=True)


def test_actual_application_auth_and_letter_persistence(client,app_module,monkeypatch):
    from tests.test_resume_draft_routes import _register_verify_login,_login,_csrf
    from tests.test_job001_service import payload
    from services.base_provider import SearchResult
    from datetime import datetime,timezone
    email='ai005-'+uuid4().hex+'@example.test'
    _register_verify_login(app_module,client,email=email,next_path='/saved-vacancies')
    raw=payload();raw['published_at']=datetime.now(timezone.utc).isoformat()
    class Provider:
        def search(self,**kwargs):return SearchResult(items=[raw],total=1,page=0,pages=1,has_next=False)
    monkeypatch.setattr(app_module,'HH_APP_TOKEN','test-only')
    monkeypatch.setattr(app_module,'HeadHunterProvider',lambda *a,**k:Provider())
    page=client.get('/vacancies?search=1&keyword=Python&source=hh')
    ref=html.unescape(re.search(r'name="reference" value="([^"]+)"',page.get_data(as_text=True)).group(1))
    saved=client.post('/saved-vacancies/save',data={'csrf_token':_csrf(page),'reference':ref}).location
    preview=client.get(saved+'/letters');body=preview.get_data(as_text=True)
    def field(key):return html.unescape(re.search(r'name="'+key+r'" value="([^"]+)"',body).group(1))
    result=client.post('/cover-letters/new',data={'csrf_token':_csrf(preview),'saved_id':field('saved_id'),
        'source_hash':field('source_hash'),'operation_key':field('operation_key'),'language':'en','length':'short','tone':'friendly','confirm':'1'})
    assert result.status_code==303
    path=result.location
    assert client.post(path+'/save',data={'csrf_token':_csrf(client.get(path)),'expected_revision':'1','subject':'Hello','body':'Actual application draft.',
        'language':'en','length':'short','tone':'friendly','confirm':'1'}).status_code==303
    client.post('/auth/logout',data={'csrf_token':_csrf(client.get('/'))})
    assert client.get(path).status_code==302
    _login(client,email=email,next_path='/cover-letters')
    assert 'Actual application draft.' in client.get(path).get_data(as_text=True)
