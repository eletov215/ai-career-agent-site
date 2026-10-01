"""Disposable SITE QA harness. Not imported by production code."""
from __future__ import annotations

import copy
import html
import json
import re
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from flask import Flask, g
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader

from database import create_database, upgrade_database
from domain.ai import ProviderError
from models import User
from routes.letter_site_qa import BASE, create_letter_site_qa_blueprint
from security import rate_limit_key
from services.ai.provider import YandexAliceProvider
from services.ai.settings import AISettings
from services.letter_site_qa import LetterSiteQA
from services.storage import StorageServices

NOW = 1789905600
ROOT = Path(__file__).resolve().parents[1]


class RecordingTransport:
    """Only the HTTP transport is fake; adapter/contract/ledger/review are real."""
    def __init__(self):
        self.calls = []
        self.failure = None
        self.before = None

    def __call__(self, payload, timeout):
        self.calls.append(copy.deepcopy(payload))
        if self.before:
            self.before()
        if self.failure == 'timeout':
            raise ProviderError('timeout_unknown')
        if self.failure == 'upstream':
            raise ProviderError('upstream_error', retryable=True)
        if self.failure == 'envelope':
            return {'ok': True, 'envelope': {'choices': []}}
        data = json.loads(payload['body']['messages'][1]['content'])
        ru = data['preferences']['language'] == 'ru'
        opening = ('\u041c\u0435\u043d\u044f \u0437\u0430\u0438\u043d\u0442\u0435\u0440\u0435\u0441\u043e\u0432\u0430\u043b\u0430 \u044d\u0442\u0430 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u044f.' if ru else 'I am applying for this position.')
        closing = ('\u0421\u043f\u0430\u0441\u0438\u0431\u043e \u0437\u0430 \u0440\u0430\u0441\u0441\u043c\u043e\u0442\u0440\u0435\u043d\u0438\u0435 \u043c\u043e\u0435\u0433\u043e \u043e\u0442\u043a\u043b\u0438\u043a\u0430.' if ru else 'Thank you for considering my application.')
        fact = data['candidate_facts'][0]
        response = {'source_hash': data['source_hash'],
                    'subject':'Отклик' if data['preferences']['language']=='ru' else 'Application',
            'paragraphs': [
                {'kind': 'opening', 'text': opening, 'candidate_evidence': [], 'vacancy_evidence': ['title']},
                {'kind': 'candidate_fit', 'text': fact['text'], 'candidate_evidence': [{'id': fact['id'], 'quote': fact['text']}], 'vacancy_evidence': []},
                {'kind': 'closing', 'text': closing, 'candidate_evidence': [], 'vacancy_evidence': []}], 'caveats': []}
        if self.failure == 'unsupported':
            response['paragraphs'][1]['text'] += ' Reduced costs by 73%.'
        raw = 'invalid JSON secret sentinel' if self.failure == 'model' else json.dumps(response)
        return {'ok': True, 'envelope': {'diagnostic': 'raw-provider-secret-sentinel',
            'choices': [{'message': {'content': raw}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 1000, 'completion_tokens': 300}}}


def build_case(directory, *, url=None, rate_enabled=False, no_logging_disabled_at=NOW - 90000):
    # No implicit DATABASE_URL. PostgreSQL callers must create an isolated schema.
    url = url or 'sqlite:///' + str(Path(directory) / 'site-qa.db')
    upgrade_database(url)
    db = create_database(url)
    admin_id, other_id, ordinary_id = str(uuid4()), str(uuid4()), str(uuid4())
    with db.session() as s, s.begin():
        for uid, email in [(admin_id, 'admin@example.test'), (other_id, 'other-admin@example.test'), (ordinary_id, 'ordinary@example.test')]:
            s.add(User(id=uid, email=email, normalized_email=email, status='active',
                       email_verified_at=NOW, created_at=NOW, updated_at=NOW))
    settings = SimpleNamespace(flask_secret_key='site-qa-test-signing-key',
        search_admin_emails=('admin@example.test', 'other-admin@example.test'),
        ai=AISettings(True, False, True, 'unit-test-api-key', 'fixture-folder',
                      'gpt://fixture-folder/aliceai-llm/latest', no_logging_disabled_at))
    storage = StorageServices.from_database(db)
    version, _ = storage.ai.read_policy()
    storage.ai.update_policy({'enabled': True, 'kill_switch': False}, expected_version=version, now=NOW)
    clock = [NOW]
    transport = RecordingTransport()
    qa = LetterSiteQA(storage, settings, enabled=True, live_enabled=True, clock=lambda: clock[0],
        provider=YandexAliceProvider(settings.ai, transport=transport))
    identity = SimpleNamespace(user=SimpleNamespace(id=admin_id, email='admin@example.test',
                              normalized_email='admin@example.test', status='active', email_verified_at=NOW))
    app = Flask(__name__, static_folder=str(ROOT / 'static'))
    app.config.update(TESTING=True, SECRET_KEY='site-qa-csrf-test-key', RATELIMIT_ENABLED=rate_enabled,
                      RATELIMIT_STORAGE_URI='memory://')
    CSRFProtect(app)
    # A separate real Limiter instance prevents this harness from reconfiguring
    # security.limiter, which belongs to the application's other route tests.
    private_limiter = Limiter(key_func=rate_limit_key, default_limits=[])
    private_limiter.init_app(app)
    @app.before_request
    def bind():
        g.current_user = identity.user
    app.jinja_loader = ChoiceLoader([DictLoader({'base.html': '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="csrf-token" content="{{ csrf_token() }}"><title>Synthetic test harness - mock transport only</title>{% block head_extra %}{% endblock %}</head><body>{% block content %}{% endblock %}</body></html>'}), FileSystemLoader(ROOT / 'templates')])
    # Decorators capture this private instance while the blueprint is built.
    # Restore the module reference before any requests; production stays intact.
    with patch('routes.letter_site_qa.limiter', private_limiter):
        app.register_blueprint(create_letter_site_qa_blueprint(settings, storage, service=qa))
    return SimpleNamespace(db=db, qa=qa, app=app, client=app.test_client(), settings=settings, storage=storage,
        limiter=private_limiter, identity=identity, admin=admin_id, other=other_id, ordinary=ordinary_id, transport=transport, clock=clock)


def field(response, name):
    body = response.get_data(as_text=True)
    match = re.search(r'name="' + re.escape(name) + r'" value="([^"]*)"', body)
    assert match, (name, response.status_code, body[:300])
    return html.unescape(match.group(1))


def prepare_http(x, language='en', length='short', tone='professional'):
    home = x.client.get(BASE)
    csrf = field(home, 'csrf_token')
    data = {'csrf_token': csrf, 'intention': field(home, 'intention'), 'language': language, 'length': length, 'tone': tone}
    response = x.client.post(BASE + '/prepare', data=data)
    assert response.status_code == 303, response.get_data(as_text=True)
    return response.location, csrf, data


def preview_http(x, path, csrf):
    response = x.client.post(path + '/preview', data={'csrf_token': csrf})
    assert response.status_code == 200, response.get_data(as_text=True)
    return field(response, 'review_token'), response
