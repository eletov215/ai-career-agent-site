"""LEGAL-001 owner routes: CSRF, stale forms, policy binding and privacy export."""
from dataclasses import replace
import html
import json
import re
import uuid
import zipfile
from io import BytesIO
from tests.test_privacy_routes import PASSWORD, _csrf, _register_verify_login


def _field(body, name):
    m = re.search(r'name="' + re.escape(name) + r'" value="([^"]*)"', body)
    assert m
    return html.unescape(m.group(1))


def _form(page):
    body = page.get_data(as_text=True)
    return {"csrf_token": _csrf(page), **{name: _field(body, name) for name in (
        "expected_record_id", "expected_revision", "consent_form_token",
    )}}


def test_consent_routes_require_login(client):
    assert client.get("/privacy-center/ai-consent", follow_redirects=False).status_code == 302


def test_accept_withdraw_replay_payload_and_export(app_module, client):
    user_id = _register_verify_login(app_module, client, email=f"legal001-{uuid.uuid4().hex}@example.test")
    page = client.get("/privacy-center/ai-consent")
    assert page.status_code == 200
    assert "DRAFT / PLACEHOLDER REQUIRED" in page.get_data(as_text=True)
    assert "Yandex AI Studio / Alice AI LLM" in page.get_data(as_text=True)
    initial = _form(page)
    assert client.post("/privacy-center/ai-consent/accept", data={
        k: v for k, v in initial.items() if k != "csrf_token"
    }).status_code == 400
    assert client.post("/privacy-center/ai-consent/accept", data={
        **initial, "legal_approved": "true"
    }).status_code == 409
    accepted = client.post("/privacy-center/ai-consent/accept", data=initial)
    assert accepted.status_code == 200
    withdrawal = _form(accepted)
    assert withdrawal["expected_revision"] == "1"
    assert client.post("/privacy-center/ai-consent/accept", data=initial).status_code == 409
    withdrawn = client.post("/privacy-center/ai-consent/withdraw", data=withdrawal)
    assert withdrawn.status_code == 200
    reaccept = _form(withdrawn)
    assert reaccept["expected_record_id"] == withdrawal["expected_record_id"]
    assert reaccept["expected_revision"] == "2"
    assert client.post("/privacy-center/ai-consent/withdraw", data=withdrawal).status_code == 409
    assert client.post("/privacy-center/ai-consent/accept", data=initial).status_code == 409
    reaccepted = client.post("/privacy-center/ai-consent/accept", data=reaccept)
    assert reaccepted.status_code == 200 and "cycle 2" in reaccepted.get_data(as_text=True)
    exported = client.post("/privacy-center/export", data={
        "csrf_token": _csrf(client.get("/privacy-center")), "password": PASSWORD,
    })
    assert exported.status_code == 200
    with zipfile.ZipFile(BytesIO(exported.data)) as archive:
        data = json.loads(archive.read("data.json"))
        manifest = json.loads(archive.read("manifest.json"))
    assert len(data["ai_consents"]) == 2 and manifest["counts"]["ai_consents"] == 2
    assert all(row["provider"] == "yandex-alice-ai-llm" for row in data["ai_consents"])
    assert user_id not in json.dumps(data["ai_consents"])


def test_empty_form_from_old_policy_cannot_accept_new_policy(app_module, client, monkeypatch):
    owner = _register_verify_login(app_module, client, email=f"legal-version-{uuid.uuid4().hex}@example.test")
    old = _form(client.get("/privacy-center/ai-consent"))
    service = app_module.CONSENT_SERVICE
    monkeypatch.setattr(service, "policy", replace(service.policy, version="test-next-draft"))
    assert client.post("/privacy-center/ai-consent/accept", data=old).status_code == 409
    assert service.repository.history(owner) == []
    fresh = _form(client.get("/privacy-center/ai-consent"))
    assert client.post("/privacy-center/ai-consent/accept", data=fresh).status_code == 200
    assert service.state(owner)["current"]["policy_version"] == "test-next-draft"


def test_form_owner_action_and_payload_binding(app_module, client):
    from werkzeug.datastructures import MultiDict
    owner = _register_verify_login(app_module, client, email=f"legal-owner-{uuid.uuid4().hex}@example.test")
    form = _form(client.get("/privacy-center/ai-consent"))
    other_client = app_module.app.test_client()
    other = _register_verify_login(app_module, other_client, email=f"legal-other-{uuid.uuid4().hex}@example.test")
    other_form = _form(other_client.get("/privacy-center/ai-consent"))
    assert other_client.post("/privacy-center/ai-consent/accept", data={
        **form, "csrf_token": other_form["csrf_token"],
    }).status_code == 409
    assert client.post("/privacy-center/ai-consent/withdraw", data=form).status_code == 409
    bad = {**form, "consent_form_token": form["consent_form_token"] + "0"}
    assert client.post("/privacy-center/ai-consent/accept", data=bad).status_code == 409
    duplicate = MultiDict(form)
    duplicate.add("expected_revision", "0")
    assert client.post("/privacy-center/ai-consent/accept", data=duplicate).status_code == 409
    assert client.post("/privacy-center/ai-consent/accept", json=form,
                       headers={"X-CSRFToken": form["csrf_token"]}).status_code == 409
    assert not app_module.STORAGE.consents.history(owner)
    assert not app_module.STORAGE.consents.history(other)
