#!/usr/bin/env python3
"""Secret-free INFRA-001 connectivity and application readiness probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import CURRENT_REVISION

SCHEMA_VERSION = 1
PACKAGE = "INFRA-001"
EXPECTED_REVISION = CURRENT_REVISION
USER_AGENT = "AI-Career-Agent-INFRA001-Probe/1.0"
MAX_BODY_BYTES = 512 * 1024

YANDEX_ENDPOINT_CATALOGUE = "https://api.cloud.yandex.net/endpoints"
YANDEX_AI_EDGE = "https://ai.api.cloud.yandex.net/"
REED_API = "https://www.reed.co.uk/api/1.0/search?keywords=python&resultsToTake=1"
OPTIONAL_PROVIDER_URLS = {
    "headhunter": "https://api.hh.ru/",
    "trudvsem": "https://opendata.trudvsem.ru/",
    "superjob": "https://api.superjob.ru/2.0/",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def normalize_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base URL must use http or https")
    if not parsed.hostname:
        raise ValueError("base URL must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("credentials are not allowed in the base URL")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain query or fragment")
    path = parsed.path.rstrip("/")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def safe_url(value: str) -> str:
    """Return a report-safe URL without credentials, query, or fragment."""
    parsed = urllib.parse.urlsplit(value)
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    return urllib.parse.urlunsplit((parsed.scheme, host + port, parsed.path, "", ""))


def resolve_host(host: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        addresses = sorted({item[4][0] for item in infos})
        return {"ok": bool(addresses), "addresses": addresses, "latency_ms": _elapsed_ms(started), "error": None}
    except OSError as exc:
        return {"ok": False, "addresses": [], "latency_ms": _elapsed_ms(started), "error": type(exc).__name__}


def tcp_probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return {"ok": True, "latency_ms": _elapsed_ms(started), "error": None}
    except OSError as exc:
        return {"ok": False, "latency_ms": _elapsed_ms(started), "error": type(exc).__name__}


def tls_probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as secure:
                certificate = secure.getpeercert()
                cipher = secure.cipher()
                return {
                    "ok": True,
                    "latency_ms": _elapsed_ms(started),
                    "protocol": secure.version(),
                    "cipher": cipher[0] if cipher else None,
                    "not_after": certificate.get("notAfter"),
                    "error": None,
                }
    except (OSError, ssl.SSLError) as exc:
        return {
            "ok": False,
            "latency_ms": _elapsed_ms(started),
            "protocol": None,
            "cipher": None,
            "not_after": None,
            "error": type(exc).__name__,
        }


def http_request(url: str, timeout: float, *, expect_json: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json" if expect_json else "*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_BODY_BYTES)
            result: dict[str, Any] = {
                "url": safe_url(url),
                "reachable": True,
                "status": response.status,
                "latency_ms": _elapsed_ms(started),
                "content_type": response.headers.get("Content-Type"),
                "error": None,
            }
            if expect_json:
                try:
                    result["json"] = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    result["json"] = None
                    result["error"] = "InvalidJSON"
            return result
    except urllib.error.HTTPError as exc:
        # An HTTP error still proves transport reachability. This is important
        # for provider endpoints that require credentials in later packages.
        return {
            "url": safe_url(url),
            "reachable": True,
            "status": exc.code,
            "latency_ms": _elapsed_ms(started),
            "content_type": exc.headers.get("Content-Type") if exc.headers else None,
            "json": None if expect_json else None,
            "error": None,
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "url": safe_url(url),
            "reachable": False,
            "status": None,
            "latency_ms": _elapsed_ms(started),
            "content_type": None,
            "json": None if expect_json else None,
            "error": type(exc).__name__,
        }


def evaluate_ready(payload: dict[str, Any] | None, expected_revision: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"ok": False, "reason": "missing_json"}
    database = payload.get("database") if isinstance(payload.get("database"), dict) else {}
    migrations = payload.get("migrations") if isinstance(payload.get("migrations"), dict) else {}
    current = migrations.get("current_revision") or database.get("revision")
    status_ok = payload.get("status") == "ok"
    database_ok = database.get("ok") is True
    revision_ok = current == expected_revision
    return {
        "ok": bool(status_ok and database_ok and revision_ok),
        "status_ok": status_ok,
        "database_ok": database_ok,
        "revision_ok": revision_ok,
        "current_revision": current,
        "expected_revision": expected_revision,
    }


def _http_ok(check: dict[str, Any], *, exact_status: int | None = None) -> bool:
    if exact_status is not None:
        return check.get("reachable") is True and check.get("status") == exact_status
    return check.get("reachable") is True


def build_report(
    args: argparse.Namespace,
    *,
    dns: Callable[[str], dict[str, Any]] = resolve_host,
    tcp: Callable[[str, int, float], dict[str, Any]] = tcp_probe,
    tls: Callable[[str, int, float], dict[str, Any]] = tls_probe,
    http: Callable[..., dict[str, Any]] = http_request,
) -> dict[str, Any]:
    base_url = normalize_base_url(args.base_url)
    parsed = urllib.parse.urlsplit(base_url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    checks: dict[str, Any] = {
        "target_dns": dns(host),
        "target_tcp": tcp(host, port, args.timeout),
        "target_tls": tls(host, port, args.timeout)
        if parsed.scheme == "https"
        else {"ok": True, "skipped": True, "reason": "target_not_https"},
        "health_live": http(base_url + "/health/live", args.timeout, expect_json=True),
        "health_ready": http(base_url + "/health/ready", args.timeout, expect_json=True),
        "home": http(base_url + "/", args.timeout, expect_json=False),
    }
    checks["ready_evaluation"] = evaluate_ready(checks["health_ready"].get("json"), args.expected_revision)

    required_names = ["target_dns", "target_tcp", "target_tls", "health_live", "health_ready", "ready_evaluation", "home"]
    required_results = {
        "target_dns": checks["target_dns"].get("ok") is True,
        "target_tcp": checks["target_tcp"].get("ok") is True,
        "target_tls": checks["target_tls"].get("ok") is True,
        "health_live": _http_ok(checks["health_live"], exact_status=200),
        "health_ready": _http_ok(checks["health_ready"], exact_status=200),
        "ready_evaluation": checks["ready_evaluation"].get("ok") is True,
        "home": _http_ok(checks["home"], exact_status=200),
    }

    if args.skip_outbound:
        checks["outbound"] = {"skipped": True}
    else:
        checks["yandex_endpoint_catalogue"] = http(YANDEX_ENDPOINT_CATALOGUE, args.timeout, expect_json=False)
        checks["yandex_ai_edge"] = http(YANDEX_AI_EDGE, args.timeout, expect_json=False)
        checks["reed_api"] = http(REED_API, args.timeout, expect_json=False)
        required_names.extend(["yandex_endpoint_catalogue", "yandex_ai_edge", "reed_api"])
        required_results.update(
            {
                "yandex_endpoint_catalogue": _http_ok(checks["yandex_endpoint_catalogue"]),
                "yandex_ai_edge": _http_ok(checks["yandex_ai_edge"]),
                "reed_api": _http_ok(checks["reed_api"]),
            }
        )
        if args.optional_providers:
            checks["optional_providers"] = {
                name: http(url, args.timeout, expect_json=False) for name, url in OPTIONAL_PROVIDER_URLS.items()
            }

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "package": PACKAGE,
        "generated_at": utc_now(),
        "candidate_id": args.candidate_id,
        "observer": {
            "country": args.country,
            "city": args.city,
            "network": args.network,
            "device": args.device,
        },
        "target": {"base_url": safe_url(base_url), "host": host, "port": port},
        "expected_revision": args.expected_revision,
        "checks": checks,
        "summary": {
            "ok": all(required_results.values()),
            "required_checks": required_names,
            "required_results": required_results,
            "passed_required_checks": sum(1 for value in required_results.values() if value),
            "failed_required_checks": [name for name, value in required_results.items() if not value],
            "report_fingerprint": None,
        },
    }
    fingerprint_source = json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    report["summary"]["report_fingerprint"] = hashlib.sha256(fingerprint_source).hexdigest()
    return report


def _mark(value: bool) -> str:
    return "PASS" if value else "FAIL"


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    observer = report["observer"]
    lines = [
        "# INFRA-001 - VPS probe report",
        "",
        "| Поле | Значение |",
        "|---|---|",
        f"| Кандидат | {report.get('candidate_id', '-')} |",
        f"| Наблюдатель | {observer.get('country', '-')} / {observer.get('city', '-')} / {observer.get('network', '-')} / {observer.get('device', '-')} |",
        f"| Target | `{report['target']['base_url']}` |",
        f"| Revision | `{report.get('expected_revision')}` |",
        f"| Итог | **{_mark(summary.get('ok') is True)}** |",
        f"| Fingerprint | `{summary.get('report_fingerprint')}` |",
        "",
        "## 1. Обязательные проверки",
        "",
        "| Проверка | Результат |",
        "|---|---:|",
    ]
    for name in summary.get("required_checks", []):
        lines.append(f"| `{name}` | {_mark(summary['required_results'].get(name) is True)} |")

    checks = report.get("checks", {})
    optional = checks.get("optional_providers")
    if isinstance(optional, dict):
        lines.extend(["", "## 2. Необязательные provider endpoints", "", "| Provider | Reachable | HTTP | Latency, ms |", "|---|---:|---:|---:|"])
        for name, check in optional.items():
            lines.append(
                f"| {name} | {_mark(check.get('reachable') is True)} | {check.get('status') or '-'} | {check.get('latency_ms') or '-'} |"
            )

    lines.extend(
        [
            "",
            "> Отчёт не содержит API keys, credentials, query strings или response bodies. Reed transport reachability не заменяет договорную проверку REED-COMPAT-001.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe an INFRA-001 VPS candidate")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--candidate-id", default="unlabelled-candidate")
    parser.add_argument("--country", default="unknown")
    parser.add_argument("--city", default="unknown")
    parser.add_argument("--network", default="unknown")
    parser.add_argument("--device", default="unknown")
    parser.add_argument("--expected-revision", default=EXPECTED_REVISION)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--skip-outbound", action="store_true")
    parser.add_argument("--optional-providers", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when a required check fails")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    json_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(report)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json_text, encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown_text, encoding="utf-8")
    print(json_text, end="")
    return 0 if (report["summary"]["ok"] or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
