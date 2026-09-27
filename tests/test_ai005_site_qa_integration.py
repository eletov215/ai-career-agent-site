"""Verify real parent registration and independent tester throttling."""
from types import SimpleNamespace

from flask import Flask, g
from flask_wtf import CSRFProtect

from routes.admin_sources import create_admin_sources_blueprint
from routes.letter_site_qa import BASE
from security import limiter
from tests.site_qa_support import build_case, field, prepare_http, preview_http, NOW


def test_enabled_child_blueprint_preview_uses_real_parent_and_stays_non_billable(tmp_path, monkeypatch):
    x = build_case(tmp_path)
    monkeypatch.setenv('AI_SITE_QA_ENABLED', '1')
    monkeypatch.setenv('AI_SITE_QA_LIVE_ENABLED', '0')
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='nested-site-qa-test', RATELIMIT_ENABLED=False)
    CSRFProtect(app)
    limiter.init_app(app)
    app.jinja_loader = x.app.jinja_loader
    @app.before_request
    def bind():
        g.current_user = x.identity.user
    app.register_blueprint(create_admin_sources_blueprint(x.settings, x.storage, SimpleNamespace()))
    client = app.test_client()
    try:
        assert 'admin_sources.letter_site_qa.home' in app.view_functions
        assert 'admin_sources.source_center' in app.view_functions
        response = client.get(BASE)
        assert response.status_code == 200
        csrf = field(response, 'csrf_token')
        response = client.post(BASE+'/prepare', data={'csrf_token':csrf,
            'intention':field(response,'intention'),'language':'en','length':'short','tone':'professional'})
        assert response.status_code == 303
        path = response.location
        response = client.post(path+'/preview',data={'csrf_token':csrf})
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert 'type="checkbox"' not in text and 'disabled' in text
        response = client.post(path+'/generate', data={'csrf_token':csrf,'review_token':field(response,'review_token')})
        assert response.status_code == 503
        assert not x.transport.calls
        x.identity.user = None
        assert client.get(BASE).status_code == 404
    finally:
        x.db.dispose()


def test_preview_throttle_does_not_mix_admins_on_the_same_ip(tmp_path):
    x = build_case(tmp_path, rate_enabled=True)
    try:
        path, csrf, _ = prepare_http(x)
        for _ in range(30):
            assert x.client.post(path+'/preview',data={'csrf_token':csrf}).status_code == 200
        assert x.client.post(path+'/preview',data={'csrf_token':csrf}).status_code == 429
        x.identity.user = SimpleNamespace(id=x.other,email='other-admin@example.test',
            normalized_email='other-admin@example.test',status='active',email_verified_at=NOW)
        path2, csrf2, _ = prepare_http(x)
        _, response = preview_http(x,path2,csrf2)
        assert response.status_code == 200 and not x.transport.calls
    finally:
        x.db.dispose()
