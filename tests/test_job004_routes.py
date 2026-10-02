from types import SimpleNamespace

import pytest
pytest.importorskip("flask")
from flask import Flask, g
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader

from routes.job_analytics import create_job_analytics_blueprint
from services.job_analytics import JobAnalyticsService


class FakeRepository:
    calls = 0
    def source_choices(self, _user):
        self.calls += 1; return ("hh",)
    def metrics(self, _user, **_filters):
        self.calls += 1
        return {"saved_count": 0, "preparing_ever_count": 0, "submitted_ever_count": 0,
            "in_process_ever_count": 0, "active_pipeline_count": 0, "closed_current_count": 0,
            **{f"state_{state}": 0 for state in ("saved", "preparing", "submitted_user_reported", "in_process_user_reported", "closed")}}


@pytest.fixture
def web():
    repo = FakeRepository(); identity = SimpleNamespace(user=SimpleNamespace(id="owner", status="active", email_verified_at=1))
    app = Flask(__name__); app.config.update(TESTING=True, SECRET_KEY="test")
    @app.before_request
    def bind(): g.current_user = identity.user
    app.add_url_rule("/auth/login", endpoint="auth.login", view_func=lambda: "login")
    app.add_url_rule("/dashboard", endpoint="dashboard", view_func=lambda: "dashboard")
    app.add_url_rule("/saved-vacancies", endpoint="saved_vacancies.index", view_func=lambda: "saved")
    app.register_blueprint(create_job_analytics_blueprint(JobAnalyticsService(repo, clock=lambda: 100)))
    app.jinja_loader = ChoiceLoader([DictLoader({"base.html": "{% block content %}{% endblock %}"}), FileSystemLoader("templates")])
    return SimpleNamespace(client=app.test_client(), identity=identity, repo=repo)


def test_private_headers_empty_truthful_copy_and_user_reported_wording(web):
    response = web.client.get("/analytics")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.headers["Cache-Control"].startswith("no-store")
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow" and "ETag" not in response.headers
    assert "нет сохранённых вакансий" in body and "0%" not in body
    assert "со слов пользователя" in body and "не подтверждённая работодателем" in body


def test_auth_verified_bounds_and_dashboard_does_not_call_analytics(web):
    web.identity.user = None
    assert web.client.get("/analytics").status_code == 302
    web.identity.user = SimpleNamespace(id="owner", status="pending", email_verified_at=1)
    assert web.client.get("/analytics").status_code == 404
    web.identity.user = SimpleNamespace(id="owner", status="active", email_verified_at=1)
    assert web.client.get("/analytics?source=" + "x" * 33).status_code == 400
    before = web.repo.calls
    assert web.client.get("/dashboard").status_code == 200 and web.repo.calls == before
