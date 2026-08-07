from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from database import CURRENT_REVISION
from scripts import infra_probe


def _args(tmp_path: Path, **overrides):
    values = {
        "base_url": "https://candidate.example",
        "candidate_id": "provider-region-plan",
        "country": "RU",
        "city": "Moscow",
        "network": "mobile",
        "device": "iphone",
        "expected_revision": CURRENT_REVISION,
        "timeout": 1.0,
        "skip_outbound": False,
        "optional_providers": True,
        "strict": True,
        "json_output": tmp_path / "report.json",
        "markdown_output": tmp_path / "report.md",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_normalize_base_url_rejects_credentials_and_query():
    with pytest.raises(ValueError):
        infra_probe.normalize_base_url("https://user:pass@example.com")
    with pytest.raises(ValueError):
        infra_probe.normalize_base_url("https://example.com/?token=secret")


def test_safe_url_removes_sensitive_parts():
    assert infra_probe.safe_url("https://user:pass@example.com/path?q=secret#fragment") == "https://example.com/path"


def test_evaluate_ready_accepts_expected_revision():
    payload = {
        "status": "ok",
        "database": {"ok": True, "revision": CURRENT_REVISION},
        "migrations": {"current_revision": CURRENT_REVISION},
    }
    result = infra_probe.evaluate_ready(payload, CURRENT_REVISION)
    assert result == {
        "ok": True,
        "status_ok": True,
        "database_ok": True,
        "revision_ok": True,
        "current_revision": CURRENT_REVISION,
        "expected_revision": CURRENT_REVISION,
    }


def test_evaluate_ready_rejects_revision_mismatch():
    payload = {"status": "ok", "database": {"ok": True, "revision": "old"}}
    assert infra_probe.evaluate_ready(payload, CURRENT_REVISION)["ok"] is False


def test_build_report_is_secret_free_and_passes(tmp_path):
    args = _args(tmp_path)

    def fake_dns(host):
        return {"ok": True, "addresses": ["203.0.113.10"], "latency_ms": 1.0, "error": None}

    def fake_tcp(host, port, timeout):
        return {"ok": True, "latency_ms": 2.0, "error": None}

    def fake_tls(host, port, timeout):
        return {"ok": True, "latency_ms": 3.0, "protocol": "TLSv1.3", "cipher": "TEST", "not_after": "later", "error": None}

    def fake_http(url, timeout, *, expect_json=False):
        payload = None
        if url.endswith("/health/live"):
            payload = {"status": "ok"}
        elif url.endswith("/health/ready"):
            payload = {
                "status": "ok",
                "database": {"ok": True, "revision": CURRENT_REVISION},
                "migrations": {"current_revision": CURRENT_REVISION},
            }
        return {
            "url": infra_probe.safe_url(url),
            "reachable": True,
            "status": 200,
            "latency_ms": 4.0,
            "content_type": "application/json",
            "json": payload,
            "error": None,
        }

    report = infra_probe.build_report(args, dns=fake_dns, tcp=fake_tcp, tls=fake_tls, http=fake_http)
    assert report["summary"]["ok"] is True
    assert report["summary"]["failed_required_checks"] == []
    serialized = json.dumps(report)
    assert "user:pass" not in serialized
    assert "keywords=python" not in serialized
    assert len(report["summary"]["report_fingerprint"]) == 64
    assert set(report["checks"]["optional_providers"]) == {"headhunter", "trudvsem", "superjob"}


def test_markdown_contains_readable_status(tmp_path):
    args = _args(tmp_path, skip_outbound=True, optional_providers=False)

    def fake_http(url, timeout, *, expect_json=False):
        payload = None
        if url.endswith("/health/ready"):
            payload = {"status": "ok", "database": {"ok": True, "revision": CURRENT_REVISION}}
        elif url.endswith("/health/live"):
            payload = {"status": "ok"}
        return {"url": infra_probe.safe_url(url), "reachable": True, "status": 200, "latency_ms": 1.0, "content_type": "application/json", "json": payload, "error": None}

    report = infra_probe.build_report(
        args,
        dns=lambda host: {"ok": True, "addresses": ["127.0.0.1"], "latency_ms": 1.0, "error": None},
        tcp=lambda host, port, timeout: {"ok": True, "latency_ms": 1.0, "error": None},
        tls=lambda host, port, timeout: {"ok": True, "latency_ms": 1.0, "protocol": "TLSv1.3", "cipher": "TEST", "not_after": "later", "error": None},
        http=fake_http,
    )
    markdown = infra_probe.render_markdown(report)
    assert "# INFRA-001 - VPS probe report" in markdown
    assert "**PASS**" in markdown
    assert "credentials" in markdown


def test_main_writes_json_and_markdown(monkeypatch, tmp_path, capsys):
    report = {
        "summary": {"ok": True, "required_checks": [], "required_results": {}, "report_fingerprint": "a" * 64},
        "observer": {"country": "RU", "city": "Moscow", "network": "mobile", "device": "iphone"},
        "target": {"base_url": "https://candidate.example"},
        "candidate_id": "candidate",
        "expected_revision": CURRENT_REVISION,
        "checks": {},
    }
    monkeypatch.setattr(infra_probe, "build_report", lambda args: report)
    json_path = tmp_path / "result.json"
    md_path = tmp_path / "result.md"
    code = infra_probe.main([
        "--base-url", "https://candidate.example",
        "--json-output", str(json_path),
        "--markdown-output", str(md_path),
        "--strict",
    ])
    assert code == 0
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["ok"] is True
    assert "INFRA-001" in md_path.read_text(encoding="utf-8")
    assert '"ok": true' in capsys.readouterr().out.lower()
