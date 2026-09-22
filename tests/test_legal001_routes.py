"""LEGAL-001 owner routes: CSRF, stale forms, replay and privacy export."""
import html
import json
import re
import uuid
import zipfile
from io import BytesIO
from tests.test_privacy_routes import PASSWORD, _csrf, _register_verify_login

def _field(body,name):
    m=re.search(r'name="'+re.escape(name)+r'" value="([^"]*)"',body)
    assert m
    return html.unescape(m.group(1))

def test_consent_routes_require_login(client):
    assert client.get("/privacy-center/ai-consent",follow_redirects=False).status_code==302

def test_accept_withdraw_replay_payload_and_export(app_module,client):
    email=f"legal001-{uuid.uuid4().hex}@example.test"
    user_id=_register_verify_login(app_module,client,email=email)
    page=client.get("/privacy-center/ai-consent")
    assert page.status_code==200
    body=page.get_data(as_text=True)
    assert "DRAFT / PLACEHOLDER REQUIRED" in body
    assert "Yandex AI Studio / Alice AI LLM" in body
    assert "не является финальным юридическим" in body
    token=_csrf(page)

    missing_csrf=client.post("/privacy-center/ai-consent/accept",
        data={"expected_record_id":"","expected_revision":"0"})
    assert missing_csrf.status_code==400

    extra=client.post("/privacy-center/ai-consent/accept",
        data={"csrf_token":token,"expected_record_id":"","expected_revision":"0","legal_approved":"true"})
    assert extra.status_code==409

    accepted=client.post("/privacy-center/ai-consent/accept",
        data={"csrf_token":_csrf(client.get("/privacy-center/ai-consent")),
              "expected_record_id":"","expected_revision":"0"})
    assert accepted.status_code==200
    body=accepted.get_data(as_text=True)
    record_id=_field(body,"expected_record_id");revision=_field(body,"expected_revision")
    assert revision=="1" and "accepted" in body

    replay=client.post("/privacy-center/ai-consent/accept",
        data={"csrf_token":_csrf(client.get("/privacy-center/ai-consent")),
              "expected_record_id":"","expected_revision":"0"})
    assert replay.status_code==409

    withdrawn=client.post("/privacy-center/ai-consent/withdraw",
        data={"csrf_token":_csrf(client.get("/privacy-center/ai-consent")),
              "expected_record_id":record_id,"expected_revision":"1"})
    assert withdrawn.status_code==200
    body=withdrawn.get_data(as_text=True)
    assert "withdrawn" in body
    assert _field(body,"expected_record_id")==record_id and _field(body,"expected_revision")=="2"

    stale_withdraw=client.post("/privacy-center/ai-consent/withdraw",
        data={"csrf_token":_csrf(client.get("/privacy-center/ai-consent")),
              "expected_record_id":record_id,"expected_revision":"1"})
    assert stale_withdraw.status_code==409

    reaccepted=client.post("/privacy-center/ai-consent/accept",
        data={"csrf_token":_csrf(client.get("/privacy-center/ai-consent")),
              "expected_record_id":record_id,"expected_revision":"2"})
    assert reaccepted.status_code==200
    assert "cycle 2" in reaccepted.get_data(as_text=True)

    exported=client.post("/privacy-center/export",
        data={"csrf_token":_csrf(client.get("/privacy-center")),"password":PASSWORD})
    assert exported.status_code==200
    with zipfile.ZipFile(BytesIO(exported.data)) as archive:
        data=json.loads(archive.read("data.json"))
        manifest=json.loads(archive.read("manifest.json"))
    assert len(data["ai_consents"])==2
    assert manifest["counts"]["ai_consents"]==2
    assert all(row["provider"]=="yandex-alice-ai-llm" for row in data["ai_consents"])
    assert user_id not in json.dumps(data["ai_consents"])
