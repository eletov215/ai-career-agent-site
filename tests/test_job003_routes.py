import html
import re
from types import SimpleNamespace

import pytest
pytest.importorskip('flask')
from flask import Flask, g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader

from domain.reminders import ReminderError
from repositories.reminders import ReminderRepository
from routes.application_trackers import create_application_trackers_blueprint
from routes.reminders import create_reminders_blueprint
from services.application_trackers import ApplicationTrackerService
from services.reminders import ReminderService
from repositories.application_trackers import ApplicationTrackerRepository
from tests.test_job001_service import job_env, reference


def csrf(response):
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"', response.get_data(as_text=True)).group(1))


@pytest.fixture
def reminder_web(job_env):
    token, _, _ = reference(job_env)
    saved = job_env.svc.save(job_env.owner, token)
    identity = SimpleNamespace(user=SimpleNamespace(id=job_env.owner, status='active', email_verified_at=1))
    reminders = ReminderService(ReminderRepository(job_env.db))
    trackers = ApplicationTrackerService(ApplicationTrackerRepository(job_env.db))
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='job003-test')
    CSRFProtect(app)
    @app.before_request
    def bind():
        g.current_user = identity.user
    app.add_url_rule('/auth/login', endpoint='auth.login', view_func=lambda: 'Login')
    app.add_url_rule('/saved-vacancies/<uuid:saved_id>', endpoint='saved_vacancies.detail', view_func=lambda saved_id: 'Saved')
    app.register_blueprint(create_reminders_blueprint(reminders))
    app.register_blueprint(create_application_trackers_blueprint(trackers, job_env.svc, reminders))
    app.jinja_loader = ChoiceLoader([DictLoader({'base.html': '<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}), FileSystemLoader('templates')])
    app.jinja_env.filters['saved_time'] = str
    return SimpleNamespace(client=app.test_client(), service=reminders, identity=identity, saved=saved, env=job_env)


def test_default_off_form_flow_enable_create_disable_hide_delete(reminder_web):
    w = reminder_web
    tracker = f"/saved-vacancies/{w.saved['id']}/tracker"
    page = w.client.get(tracker)
    token = csrf(page)
    body = page.get_data(as_text=True)
    assert 'Напоминания выключены' in body and 'name="due_date"' not in body
    rejected = w.client.post(f"/saved-vacancies/{w.saved['id']}/reminder", data={
        'csrf_token': token, 'due_date': '2026-10-03', 'expected_revision': '0'})
    assert rejected.status_code == 400 and 'Сначала включите напоминания' in rejected.get_data(as_text=True)

    settings = w.client.get('/reminders')
    token = csrf(settings)
    assert w.client.post('/reminders/preference', data={
        'csrf_token': token, 'enabled': '1', 'expected_revision': '0'}).status_code == 303
    assert w.client.post(f"/saved-vacancies/{w.saved['id']}/reminder", data={
        'csrf_token': token, 'due_date': '2026-10-03', 'expected_revision': '0'}).status_code == 303
    assert 'name="due_date"' in w.client.get(tracker).get_data(as_text=True)

    assert w.client.post('/reminders/preference', data={
        'csrf_token': token, 'enabled': '0', 'expected_revision': '1'}).status_code == 303
    disabled = w.client.get(tracker)
    body = disabled.get_data(as_text=True)
    assert 'не является активным уведомлением' in body and 'name="due_date"' not in body
    assert '2026-10-03' not in w.client.get('/reminders').get_data(as_text=True)
    token = csrf(disabled)
    assert w.client.post(f"/saved-vacancies/{w.saved['id']}/reminder/delete", data={
        'csrf_token': token, 'expected_revision': '1'}).status_code == 303
    assert w.service.for_saved(w.env.owner, w.saved['id']) is None


def test_repository_opt_in_stale_write_and_cross_owner_boundaries(reminder_web):
    w = reminder_web
    with pytest.raises(ReminderError, match='preference_disabled'):
        w.service.save(w.env.owner, w.saved['id'], '2026-10-03', 0, now=1)
    w.service.set_preference(w.env.owner, True, 0, now=1)
    row = w.service.save(w.env.owner, w.saved['id'], '2026-10-03', 0, now=1)
    with pytest.raises(ReminderError, match='stale_write'):
        w.service.save(w.env.owner, w.saved['id'], '2026-10-04', 0, now=2)
    with pytest.raises(ReminderError, match='not_found'):
        w.service.for_saved(w.env.other, w.saved['id'])
    w.service.set_preference(w.env.owner, False, 1, now=2)
    assert w.service.list(w.env.owner) == []
    assert w.service.for_saved(w.env.owner, w.saved['id']) == row
