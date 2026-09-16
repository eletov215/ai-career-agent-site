"""Real Flask/CSRF private UI tests; no provider or email traffic."""
from types import SimpleNamespace
import html
import json
import re
from uuid import uuid4

import pytest
pytest.importorskip('flask', reason='Flask route execution is mandatory in installed GitHub CI')
from flask import Flask, g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from werkzeug.datastructures import MultiDict
from routes.resume_interview import create_resume_interview_blueprint
from services.ai.interview_reference import ROOT
from tests.test_ai003_service import env, start, review, command, confirm_command


@pytest.fixture
def web(env):
    db, owner_id, other_id, svc = env
    owner = SimpleNamespace(id=owner_id, status='active', email_verified_at=1, normalized_email='admin@example.invalid')
    settings = SimpleNamespace(ai_interview_review_enabled=True, search_admin_emails=('admin@example.invalid',))
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='test-only')
    CSRFProtect(app)
    @app.before_request
    def identity():
        g.current_user = owner
    app.register_blueprint(create_resume_interview_blueprint(svc, settings))
    app.add_url_rule('/resumes', endpoint='resume_drafts.library', view_func=lambda: '')
    app.add_url_rule('/resume-builder/<draft_id>', endpoint='resume_drafts.builder', view_func=lambda draft_id: '')
    app.add_url_rule('/resumes/<draft_id>/delete', endpoint='resume_drafts.delete_draft', view_func=lambda draft_id: '', methods=['POST'])
    app.jinja_loader = ChoiceLoader([
        DictLoader({'base.html': '<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),
        FileSystemLoader(ROOT/'templates'),
    ])
    return app.test_client(), owner, settings, env


def csrf(response):
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"', response.get_data(as_text=True)).group(1))


def form(result, token, **changes):
    return {'csrf_token': token, 'action': 'answer', 'expected_revision': str(result['revision']),
            'source_hash': result['source_hash'], 'operation_key': str(uuid4()),
            'node_id': result['current_node_id'], 'choice_id': 'specific', **changes}


def test_private_gate_and_no_generation_links_by_default(web):
    client, user, settings, env = web
    result = start(env)
    urls = ['/ai-interview', f"/resume-builder/{result['draft_id']}/interview", f"/api/resume-interviews/{result['id']}"]
    settings.ai_interview_review_enabled = False
    for url in urls:
        assert client.get(url).status_code == 404
    settings.ai_interview_review_enabled = True
    for changes in ({'normalized_email': 'not-admin@example.invalid'}, {'email_verified_at': None}, {'status': 'pending'}):
        for key, value in changes.items():
            old = getattr(user, key);setattr(user, key, value)
            assert all(client.get(url).status_code == 404 for url in urls)
            setattr(user, key, old)


def test_form_start_answer_restore_and_confirm(web):
    client, user, settings, env = web
    svc = env[-1]
    page = client.get('/ai-interview')
    token = csrf(page)
    choice = svc.choices()[0]
    started = client.post('/ai-interview/start', data={'csrf_token': token, 'fixture_id': choice['fixture_id'],
        'source_hash': choice['source_hash'], 'operation_key': str(uuid4())})
    assert started.status_code == 303
    page = client.get(started.location)
    assert page.status_code == 200 and page.headers['X-Robots-Tag'] == 'noindex, nofollow'
    assert 'no-store' in page.headers['Cache-Control']
    result = svc.get(user.id, svc.history(user.id)[0]['id'])
    for choice_id in ('vague', 'specific', 'measured', 'verified'):
        response = client.post(f"/ai-interview/{result['id']}/actions", data=form(result, token, choice_id=choice_id))
        assert response.status_code == 303
        result = svc.get(user.id, result['id'])
        assert client.get(response.location).status_code == 200
    assert result['status'] == 'review'
    data = {'csrf_token': token, 'action': 'confirm', 'expected_revision': str(result['revision']),
        'source_hash': result['source_hash'], 'operation_key': str(uuid4()),
        'selected_fact_ids': [f['id'] for f in result['suggestions']], 'confirm': '1'}
    confirmed = client.post(f"/ai-interview/{result['id']}/actions", data=data)
    assert confirmed.status_code == 303
    final_page = client.get(confirmed.location).get_data(as_text=True)
    assert 'name="confirm"' not in final_page and 'name="answer_index"' not in final_page
    env[0].dispose()
    assert client.get(confirmed.location).status_code == 200


def test_post_requires_csrf_and_rejects_free_text_upload_and_duplicate_fields(web):
    from io import BytesIO
    client, user, settings, env = web
    result = start(env);url = f"/ai-interview/{result['id']}/actions"
    assert client.post(url, data={}).status_code == 400
    token = csrf(client.get('/ai-interview'))
    data = form(result, token)
    for extra in ({'answer': 'real data'}, {'resume': 'real resume'}, {'draft_id': result['draft_id']}):
        assert client.post(url, data={**data, **extra}).status_code == 400
    duplicate = MultiDict(data);duplicate.add('choice_id', 'vague')
    assert client.post(url, data=duplicate).status_code == 400
    assert client.post(url, data={**data, 'file': (BytesIO(b'private'), 'cv.txt')}).status_code == 400
    assert env[-1].get(user.id, result['id'])['revision'] == 1


def test_api_strict_objects_confirm_booleans_and_payloads(web):
    client, user, settings, env = web
    result = start(env);url = f"/api/resume-interviews/{result['id']}/actions"
    token = csrf(client.get('/ai-interview'));headers = {'X-CSRF-Token': token}
    payload = form(result, token);payload.pop('csrf_token');payload['expected_revision'] = result['revision']
    for invalid in ([], 'user text', {**payload, 'resume': 'private'}, {**payload, 'action': []},
                    {**payload, 'expected_revision': True}, {**payload, 'confirm': 'yes'}, {**payload, 'selected_fact_ids': None}):
        assert client.post(url, json=invalid, headers=headers).status_code == 400
    duplicate = json.dumps(payload)[:-1] + ',"action":"answer"}'
    assert client.post(url, data=duplicate, content_type='application/json', headers=headers).status_code == 400
    assert client.post(url, data=json.dumps(payload), content_type='text/plain', headers=headers).status_code == 400
    good = client.post(url, json=payload, headers=headers)
    assert good.status_code == 200 and good.json['interview']['revision'] == 2
    repeat = client.post(url, json=payload, headers=headers)
    assert repeat.status_code == 200 and repeat.json['interview']['revision'] == 2
    assert 'operation_hash' not in good.get_data(as_text=True)


def test_cross_owner_get_api_and_post_are_hidden(web):
    client, user, settings, env = web
    result = start(env)
    token = csrf(client.get('/ai-interview'))
    user.id = env[2]
    assert client.get(f"/resume-builder/{result['draft_id']}/interview").status_code == 404
    assert client.get(f"/api/resume-interviews/{result['id']}").status_code == 404
    assert client.post(f"/ai-interview/{result['id']}/actions", data=form(result, token)).status_code == 404


def test_conflict_and_storage_error_have_safe_messages(web, monkeypatch):
    from sqlalchemy.exc import OperationalError
    client, user, settings, env = web
    result = start(env);token = csrf(client.get('/ai-interview'))
    url = f"/ai-interview/{result['id']}/actions"
    assert client.post(url, data=form(result, token)).status_code == 303
    stale = client.post(url, data=form(result, token))
    assert stale.status_code == 409 and 'Traceback' not in stale.get_data(as_text=True)
    def failed(*args, **kwargs):
        raise OperationalError('query secret', {'password': 'do-not-show'}, RuntimeError('raw secret'))
    monkeypatch.setattr(env[-1], 'execute', failed)
    error = client.post(url, data=form(result, token))
    assert error.status_code == 503 and 'do-not-show' not in error.get_data(as_text=True)


def test_real_app_registers_gate_and_keeps_public_ai_manual(client, app_module):
    assert client.get('/ai-interview').status_code == 404
    result = client.get('/api/ai/status')
    assert result.status_code == 200
    assert result.json['generation_available'] is False and result.json['mode'] == 'manual'
    rules = {str(rule) for rule in app_module.app.url_map.iter_rules()}
    assert '/resume-builder/<uuid:draft_id>/interview' in rules
