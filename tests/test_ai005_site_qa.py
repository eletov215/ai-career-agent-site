"""AI-005 SITE QA: admin-only fixed synthetic browser path. No external calls."""
from __future__ import annotations

import html
import json
import re
import time
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
pytest.importorskip("flask", reason="Pinned Flask required for SITE QA HTTP verification")
from flask import Flask, g
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from sqlalchemy import select

from models.cover_letter import CoverLetter
from repositories.ai import AIRepository
from repositories.cover_letters import CoverLetterRepository
from routes.ai005_site_qa import create_ai005_site_qa_blueprint
from services.ai.letter_admission import synthetic_cases
from services.ai.letter_site_qa import AliceLetterSiteQA
from services.ai.provider import YandexAliceProvider
from services.ai.service import AIService
from services.ai.settings import AISettings
from tests.test_ai005_service import letters

NOW = int(time.time())


class SyntheticTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, payload, timeout):
        self.calls.append(payload)
        request = json.loads(payload["body"]["messages"][1]["content"])
        fact = request["candidate_facts"][0]
        vacancy = request["vacancy"]
        language = request["preferences"]["language"]
        if language == "ru":
            paragraphs = [
                {"kind": "opening", "text": "Хочу откликнуться на эту вакансию.",
                 "candidate_evidence": [], "vacancy_evidence": ["title"]},
                {"kind": "candidate_fit", "text": fact["text"],
                 "candidate_evidence": [{"id": fact["id"], "quote": fact["text"]}], "vacancy_evidence": []},
                {"kind": "closing", "text": "Буду рад обсудить задачи роли.",
                 "candidate_evidence": [], "vacancy_evidence": []},
            ]
            subject = "Отклик: " + vacancy["title"]
        else:
            paragraphs = [
                {"kind": "opening", "text": "I would like to apply for this role.",
                 "candidate_evidence": [], "vacancy_evidence": ["title"]},
                {"kind": "candidate_fit", "text": fact["text"],
                 "candidate_evidence": [{"id": fact["id"], "quote": fact["text"]}], "vacancy_evidence": []},
                {"kind": "closing", "text": "I would welcome a conversation about the role.",
                 "candidate_evidence": [], "vacancy_evidence": []},
            ]
            subject = "Application: " + vacancy["title"]
        body = {"source_hash": request["source_hash"], "subject": subject,
                "paragraphs": paragraphs, "caveats": []}
        return {"ok": True, "envelope": {"choices": [{"message": {"content": json.dumps(body, ensure_ascii=False)},
                 "finish_reason": "stop"}], "usage": {"prompt_tokens": 700, "completion_tokens": 200}}}


@pytest.fixture
def siteqa(letters):
    ledger = AIRepository(letters.db)
    version, _ = ledger.read_policy()
    ledger.update_policy({
        "enabled": True,
        "kill_switch": False,
        "pricing_checked_on": date.today().isoformat(),
    }, expected_version=version, now=NOW)
    settings = AISettings(
        True, False, True, "test-only-key", "fixture-folder",
        "gpt://fixture-folder/aliceai-llm/latest", NOW - 90000,
    )
    transport = SyntheticTransport()
    ai = AIService(
        ledger, settings, fingerprint_key="site-qa-ledger-test",
        provider=YandexAliceProvider(settings, transport=transport), clock=lambda: NOW,
    )
    service = AliceLetterSiteQA(
        CoverLetterRepository(letters.db), ai,
        signing_key="site-qa-signing-test", clock=lambda: NOW,
    )
    return SimpleNamespace(base=letters, service=service, transport=transport)


@pytest.mark.parametrize("language,length,tone", [
    ("ru", "short", "professional"),
    ("ru", "full", "professional"),
    ("ru", "short", "friendly"),
    ("en", "short", "professional"),
    ("en", "full", "professional"),
    ("en", "short", "friendly"),
])
def test_matrix_preview_is_fixed_synthetic_and_not_admin_profile(siteqa, language, length, tone):
    result = siteqa.service.start(siteqa.base.owner, language, length, tone)
    preview = result["preview"]
    case = synthetic_cases()[language]
    assert preview["projection"]["candidate_facts"] == case["candidate_facts"]
    assert preview["projection"]["vacancy"] == case["vacancy"]
    assert preview["projection"]["preferences"] == {
        "language": language, "length": length, "tone": tone,
    }
    encoded = json.dumps(preview["projection"], ensure_ascii=False)
    assert "Built REST API tests in Python." not in encoded
    assert "private@example.test" not in encoded
    with siteqa.base.db.session() as session:
        row = session.scalar(select(CoverLetter).where(CoverLetter.id == result["letter"]["id"]))
        assert row.user_id != siteqa.base.owner
    assert not siteqa.transport.calls


def test_generate_duplicate_accept_edit_history_and_txt(siteqa):
    started = siteqa.service.start(siteqa.base.owner, "en", "short", "professional")
    letter = started["letter"]
    first = siteqa.service.generate(siteqa.base.owner, "en", letter["id"], started["preview"]["review_token"])
    second = siteqa.service.generate(siteqa.base.owner, "en", letter["id"], started["preview"]["review_token"])
    assert first["status"] == second["status"] == "proposal"
    assert first["proposal"]["id"] == second["proposal"]["id"]
    assert len(siteqa.transport.calls) == 1
    proposal = first["proposal"]
    body = proposal["content"]["body"] + "\nHuman QA edit."
    saved = siteqa.service.accept(
        siteqa.base.owner, "en", letter["id"],
        expected=str(proposal["base_revision"]), proposal_id=proposal["id"],
        subject=proposal["content"]["subject"], body=body, confirmed=True,
    )
    assert saved["last_version"] == 1
    version = siteqa.service.version(siteqa.base.owner, "en", letter["id"], 1)
    assert version["origin"] == "user_edited_alice_draft"
    assert body in siteqa.service.export(siteqa.base.owner, "en", letter["id"], 1).decode("utf-8-sig")


def _csrf(client, path="/ai-cover-letter-qa/review"):
    raw = client.get(path).get_data(as_text=True)
    return html.unescape(re.search(r'name="csrf-token" content="([^"]+)"', raw).group(1))


@pytest.fixture
def web(siteqa):
    identity = SimpleNamespace(user=SimpleNamespace(
        id=siteqa.base.owner, status="active", email_verified_at=NOW,
        email="admin@example.test", normalized_email="admin@example.test",
    ))
    settings = SimpleNamespace(search_admin_emails=("admin@example.test",))
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="site-qa-http-test")
    CSRFProtect(app)

    @app.before_request
    def bind():
        g.current_user = identity.user

    app.register_blueprint(create_ai005_site_qa_blueprint(siteqa.service, settings))
    app.jinja_loader = ChoiceLoader([
        DictLoader({"base.html": '<meta name="csrf-token" content="{{ csrf_token() }}">{% block head_extra %}{% endblock %}{% block content %}{% endblock %}'}),
        FileSystemLoader(Path(__file__).resolve().parents[1] / "templates"),
    ])
    return SimpleNamespace(client=app.test_client(), identity=identity, siteqa=siteqa)


def test_admin_session_gate_preview_has_one_generate_button_and_no_call_checkbox(web):
    c = web.client
    assert c.get("/ai-cover-letter-qa").status_code == 404
    token = _csrf(c)
    opened = c.post("/ai-cover-letter-qa/review/enable", data={"csrf_token": token})
    assert opened.status_code == 303
    page = c.get(opened.location)
    assert page.status_code == 200 and "synthetic" in page.get_data(as_text=True).lower()
    start = c.post("/ai-cover-letter-qa/start", data={
        "csrf_token": _csrf(c, "/ai-cover-letter-qa"),
        "language": "ru", "length": "short", "tone": "professional",
    })
    text = start.get_data(as_text=True)
    assert start.status_code == 200
    assert "Создать черновик с Алисой" in text
    assert 'name="confirm"' not in text
    assert "Поддерживаю API на Python" in text
    assert "Built REST API tests in Python." not in text
    assert not web.siteqa.transport.calls


def test_non_admin_csrf_unknown_fields_and_owner_isolation(web):
    c = web.client
    token = _csrf(c)
    c.post("/ai-cover-letter-qa/review/enable", data={"csrf_token": token})
    assert c.post("/ai-cover-letter-qa/start", data={
        "language": "en", "length": "short", "tone": "professional",
    }).status_code == 400
    assert c.post("/ai-cover-letter-qa/start", data={
        "csrf_token": _csrf(c, "/ai-cover-letter-qa"), "language": "en",
        "length": "short", "tone": "professional", "candidate_text": "real data",
    }).status_code == 400
    web.identity.user.email = web.identity.user.normalized_email = "other@example.test"
    assert c.get("/ai-cover-letter-qa/review").status_code == 404
