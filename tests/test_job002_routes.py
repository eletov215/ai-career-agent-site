import html, re
from pathlib import Path
from types import SimpleNamespace
import pytest
pytest.importorskip('flask')
from flask import Flask, g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from repositories.application_trackers import ApplicationTrackerRepository
from routes.application_trackers import create_application_trackers_blueprint
from routes.saved_vacancies import create_saved_vacancies_blueprint
from services.application_trackers import ApplicationTrackerService
from tests.test_job001_service import job_env, reference

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def tracker_web(job_env):
    token,_,_=reference(job_env);saved=job_env.svc.save(job_env.owner,token)
    identity=SimpleNamespace(user=SimpleNamespace(id=job_env.owner,status='active',email_verified_at=1))
    app=Flask(__name__);app.config.update(TESTING=True,SECRET_KEY='job002-test');CSRFProtect(app)
    @app.before_request
    def bind():g.current_user=identity.user
    app.add_url_rule('/auth/login',endpoint='auth.login',view_func=lambda:'Login')
    app.register_blueprint(create_saved_vacancies_blueprint(job_env.svc))
    service=ApplicationTrackerService(ApplicationTrackerRepository(job_env.db))
    app.register_blueprint(create_application_trackers_blueprint(service,job_env.svc))
    app.jinja_loader=ChoiceLoader([DictLoader({'base.html':'<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),FileSystemLoader(ROOT/'templates')])
    return SimpleNamespace(client=app.test_client(),identity=identity,saved=saved,env=job_env,
                           service=service)


def csrf(response):
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"',response.get_data(as_text=True)).group(1))


def test_private_native_tracker_flow_wording_conflict_and_validation(tracker_web):
    w=tracker_web;url=f"/saved-vacancies/{w.saved['id']}/tracker";page=w.client.get(url)
    assert page.status_code==200 and 'no-store' in page.headers['Cache-Control']
    body=page.get_data(as_text=True)
    assert 'не отправляет отклик работодателю' in body and 'не получает подтверждение от работодателя' in body
    token=csrf(page)
    assert w.client.post(url,data={'state':'preparing','expected_revision':'0'}).status_code==400
    assert w.client.post(url,json={'state':'preparing','expected_revision':0},headers={'X-CSRF-Token':token}).status_code==400
    assert w.client.post(url,data={'csrf_token':token,'state':'submitted_user_reported','expected_revision':'0'}).status_code==303
    changed=w.client.get(url).get_data(as_text=True)
    assert 'записан пользователем и не подтверждён работодателем' in changed
    stale=w.client.post(url,data={'csrf_token':token,'state':'closed','expected_revision':'0'})
    assert stale.status_code==409 and 'другой вкладке' in stale.get_data(as_text=True)


def test_tracker_cross_owner_is_404(tracker_web):
    w=tracker_web;w.identity.user.id=w.env.other
    url=f"/saved-vacancies/{w.saved['id']}/tracker"
    assert w.client.get(url).status_code==404


def test_same_second_history_renders_actual_transition_chain(tracker_web):
    w=tracker_web
    w.service.transition(w.env.owner,w.saved['id'],'submitted_user_reported',0,now=10)
    w.service.transition(w.env.owner,w.saved['id'],'in_process_user_reported',1,now=10)
    body=w.client.get(f"/saved-vacancies/{w.saved['id']}/tracker").get_data(as_text=True)
    latest='Отклик отправлен (со слов пользователя) → Процесс продолжается (со слов пользователя)'
    first='Сохранено → Отклик отправлен (со слов пользователя)'
    assert body.index(latest) < body.index(first)
