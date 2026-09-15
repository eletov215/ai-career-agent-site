"""Private reference UI E2E in CI. All paid network remains blocked."""
from types import SimpleNamespace
import json
from uuid import uuid4
import re
import pytest
pytest.importorskip('flask')
from flask import Flask,g
from flask_wtf import CSRFProtect
from routes.resume_analysis import create_resume_analysis_blueprint
from test_ai002_service import env

@pytest.fixture
def web(env):
    svc=env[-1];uid=env[1];owner=SimpleNamespace(id=uid,status='active',email_verified_at=1,normalized_email='review@example.invalid')
    settings=SimpleNamespace(ai_analysis_review_enabled=True,search_admin_emails=('review@example.invalid',))
    app=Flask(__name__);app.config.update(TESTING=True,SECRET_KEY='test-only')
    CSRFProtect(app)
    @app.before_request
    def identity():g.current_user=owner
    app.register_blueprint(create_resume_analysis_blueprint(svc,settings))
    # Supply a tiny parent template; feature templates are loaded exactly as shipped.
    from jinja2 import ChoiceLoader,DictLoader,FileSystemLoader
    from services.resume_analysis import ROOT
    app.jinja_loader=ChoiceLoader([DictLoader({'base.html':'<meta name="csrf-token" content="{{ csrf_token() }}">{% block content %}{% endblock %}'}),FileSystemLoader(ROOT/'templates')])
    return app.test_client(),settings,owner,svc

def csrf(page):return re.search(r'name="csrf-token" content="([^"]+)"',page.get_data(as_text=True)).group(1)

def test_reference_UI_closed_for_anonymous_nonadmin_and_flag_off(web):
    client,settings,owner,svc=web
    settings.ai_analysis_review_enabled=False;assert client.get('/ai-analysis').status_code==404
    settings.ai_analysis_review_enabled=True;owner.normalized_email='other@example.invalid';assert client.get('/ai-analysis').status_code==404
    owner.normalized_email='review@example.invalid';owner.email_verified_at=None;assert client.get('/ai-analysis').status_code==404

def test_reference_ui_creates_reviews_and_reads_without_provider(web,monkeypatch):
    client,settings,owner,svc=web
    def forbidden(*a,**k):raise AssertionError('no provider calls')
    monkeypatch.setattr(svc.runtime,'generate',forbidden)
    page=client.get('/ai-analysis');assert page.status_code==200 and 'no-store' in page.headers['Cache-Control']
    r=client.post('/ai-analysis/reference',data={'csrf_token':csrf(page),'fixture_id':'resume-analysis-en-01','source_hash':svc.source('resume-analysis-en-01')[2],'operation_key':str(uuid4())})
    assert r.status_code==303
    detail=client.get(r.location);assert detail.status_code==200 and 'Data analysis experience' in detail.get_data(as_text=True)
    report=svc.history(owner.id)[0];full=svc.get(owner.id,report['id'])
    posted=client.post(r.location+'/review',data={'csrf_token':csrf(detail),'recommendation_id':'rec-1','decision':'accepted','expected_revision':'0','source_hash':full['source_hash']})
    assert posted.status_code==303
    assert svc.get(owner.id,report['id'])['decisions']['rec-1']['decision']=='accepted'
    stale=client.post(r.location+'/review',data={'csrf_token':csrf(detail),'recommendation_id':'rec-1','decision':'rejected','expected_revision':'0','source_hash':full['source_hash']})
    assert stale.status_code==409

def test_post_requires_csrf_and_rejects_real_data_or_duplicate_form_fields(web):
    from werkzeug.datastructures import MultiDict
    client,settings,owner,svc=web
    assert client.post('/ai-analysis/reference',data={}).status_code==400
    token=csrf(client.get('/ai-analysis'))
    data={'csrf_token':token,'fixture_id':'resume-analysis-en-01','source_hash':svc.source('resume-analysis-en-01')[2],'operation_key':str(uuid4())}
    assert client.post('/ai-analysis/reference',data={**data,'resume':'personal data'}).status_code==400
    assert client.post('/ai-analysis/reference',json=data,headers={'X-CSRFToken':token}).status_code==400
    duplicate=MultiDict(data);duplicate.add('fixture_id','resume-analysis-ru-01')
    assert client.post('/ai-analysis/reference',data=duplicate).status_code==400
    assert not svc.history(owner.id)

def test_cross_owner_direct_link_is_404_and_user_text_is_escaped(web):
    from domain.resume_analysis import AnalysisRequest
    client,settings,owner,svc=web
    fid='resume-analysis-en-01';r=svc.create_reference(AnalysisRequest(owner.id,str(uuid4()),fid,svc.source(fid)[2])).report
    original_owner=owner.id;owner.id=str(uuid4())
    assert client.get('/ai-analysis/'+r['id']).status_code==404
    owner.id=original_owner
    # A corrupt stored string must still be HTML-escaped even if validation is bypassed.
    from sqlalchemy import update
    from models.resume_analysis import ResumeAnalysisReport
    body=r['result'];body['summary']='<script>doBadThing()</script>'
    with svc.repository.session() as s,s.begin():s.execute(update(ResumeAnalysisReport).where(ResumeAnalysisReport.id==r['id']).values(result_json=json.dumps(body)))
    html=client.get('/ai-analysis/'+r['id']).get_data(as_text=True)
    assert '<script>doBadThing()</script>' not in html and '&lt;script&gt;' in html
