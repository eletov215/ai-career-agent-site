"""AI-005 SITE QA HTTP path: fixed synthetic data, admin-only, zero live network."""
from __future__ import annotations

import html
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
pytest.importorskip("flask", reason="Flask dependencies required for SITE QA route tests")
from flask import Flask, g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from werkzeug.datastructures import MultiDict

from routes.alice_site_qa import create_alice_site_qa_blueprint
from routes.cover_letters import create_cover_letters_blueprint
from services.alice_site_qa import AliceSiteQAService
from tests.test_ai005_live_runtime import NOW, live
from tests.test_ai005_service import letters


@pytest.fixture
def site_qa(live):
    identity=SimpleNamespace(user=SimpleNamespace(
        id=live.e.owner,status="active",email_verified_at=1,
        email="owner@example.test",normalized_email="owner@example.test"))
    settings=SimpleNamespace(search_admin_emails=("owner@example.test",))
    service=AliceSiteQAService(
        live.e.svc.repository,live.runtime,signing_key="site-qa-signing-key",clock=lambda:NOW)
    app=Flask(__name__)
    app.config.update(TESTING=True,SECRET_KEY="site-qa-flask-key")
    CSRFProtect(app)

    @app.before_request
    def bind():
        g.current_user=identity.user

    app.add_url_rule("/auth/login",endpoint="auth.login",view_func=lambda:"Login")
    app.add_url_rule("/vacancies",endpoint="vacancies",view_func=lambda:"Search")
    app.register_blueprint(create_cover_letters_blueprint(live.e.svc))
    app.register_blueprint(create_alice_site_qa_blueprint(settings,service))
    app.jinja_loader=ChoiceLoader([
        DictLoader({"base.html":'<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),
        FileSystemLoader(Path(__file__).resolve().parents[1]/"templates"),
    ])
    return SimpleNamespace(
        client=app.test_client(),identity=identity,settings=settings,service=service,live=live)


def csrf(client):
    raw=client.get("/admin/alice-qa").get_data(as_text=True)
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"',raw).group(1))


@pytest.mark.parametrize("language,length,tone",[
    ("ru","short","professional"),
    ("ru","full","professional"),
    ("ru","short","friendly"),
    ("en","short","professional"),
    ("en","full","professional"),
    ("en","short","friendly"),
])
def test_preview_matrix_is_synthetic_and_has_one_action_without_confirmation_checkbox(site_qa,language,length,tone):
    c=site_qa.client
    response=c.post("/admin/alice-qa/preview",data={
        "csrf_token":csrf(c),"language":language,"length":length,"tone":tone})
    assert response.status_code==200
    body=response.get_data(as_text=True)
    assert "Синтетический тест" in body
    assert 'name="review_token"' in body
    assert 'name="confirm"' not in body
    assert "Создать черновик с Алисой" in body
    assert "private@example.test" not in body
    assert not site_qa.live.transport.calls
    assert "no-store" in response.headers["Cache-Control"]
    assert response.headers["X-Robots-Tag"]=="noindex, nofollow"


def test_site_qa_uses_fixed_fixture_and_real_runtime_adapter_then_reuses_proposal(site_qa):
    c=site_qa.client
    preview=c.post("/admin/alice-qa/preview",data={
        "csrf_token":csrf(c),"language":"en","length":"short","tone":"professional"})
    body=preview.get_data(as_text=True)
    token=html.unescape(re.search(r'name="review_token" value="([^"]+)"',body).group(1))
    action=html.unescape(re.search(r'<form method="post" class="ai005-card" action="([^"]+/generate)">',body).group(1))
    payload={"csrf_token":csrf(c),"review_token":token}
    first=c.post(action,data=payload)
    assert first.status_code==303 and "?proposal=" in first.location
    proposal=c.get(first.location)
    text=proposal.get_data(as_text=True)
    assert proposal.status_code==200
    assert "Черновик Алисы" in text
    assert "I maintain Python APIs and write SQL queries." in str(site_qa.live.transport.calls[0])
    sent=str(site_qa.live.transport.calls[0])
    assert site_qa.live.e.owner not in sent
    assert "private@example.test" not in sent
    assert len(site_qa.live.transport.calls)==1

    second=c.post(action,data={"csrf_token":csrf(c),"review_token":token})
    assert second.status_code==303
    assert second.location==first.location
    assert len(site_qa.live.transport.calls)==1


def test_site_qa_rejects_non_admin_csrf_extra_fields_json_and_duplicate_values(site_qa):
    c=site_qa.client
    token=csrf(c)
    site_qa.identity.user.email="other@example.test"
    site_qa.identity.user.normalized_email="other@example.test"
    assert c.get("/admin/alice-qa").status_code==404
    site_qa.identity.user.email="owner@example.test"
    site_qa.identity.user.normalized_email="owner@example.test"

    valid={"csrf_token":token,"language":"en","length":"short","tone":"professional"}
    assert c.post("/admin/alice-qa/preview",data={k:v for k,v in valid.items() if k!="csrf_token"}).status_code==400
    assert c.post("/admin/alice-qa/preview",data={**valid,"candidate_fact":"real data"}).status_code==400
    assert c.post("/admin/alice-qa/preview",json=valid,headers={"X-CSRFToken":token}).status_code==400
    multi=MultiDict(valid);multi.add("language","ru")
    assert c.post("/admin/alice-qa/preview",data=multi).status_code==400
    assert not site_qa.live.transport.calls


def test_site_qa_workspace_does_not_read_real_profile(site_qa):
    prepared=site_qa.service.prepare(site_qa.live.e.owner,"en","short","professional")
    source=site_qa.live.e.svc.get(site_qa.live.e.owner,prepared["letter"]["id"])["source"]
    assert source["candidate_origin"]=="synthetic_site_qa"
    assert source["profile_version"]==0 and source["profile_hash"]==""
    assert source["facts"]==[{"id":"profile.summary","text":"I maintain Python APIs and write SQL queries."}]
    assert "Built REST API tests in Python." not in str(source)
    assert not site_qa.live.transport.calls
