#!/usr/bin/env python3
"""Send a sanitised OPS-001 test alert to OPS_ALERT_WEBHOOK_URL."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests


def main() -> int:
    url = os.getenv("OPS_ALERT_WEBHOOK_URL", "").strip()
    if not url:
        print(json.dumps({"ok": False, "error": "OPS_ALERT_WEBHOOK_URL is required"}))
        return 1
    parsed = urlparse(url)
    environment = os.getenv("APP_ENV", "production")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        print(json.dumps({"ok": False, "error": "Invalid alert webhook URL"}))
        return 1
    if environment == "production" and parsed.scheme != "https":
        print(json.dumps({"ok": False, "error": "Production webhook must use HTTPS"}))
        return 1

    token = os.getenv("OPS_ALERT_WEBHOOK_TOKEN", "").strip()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "AI-Career-Agent-Ops/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "event": "ops_test_alert",
        "service": os.getenv("SERVICE_NAME", "ai-career-agent"),
        "environment": environment,
        "version": os.getenv("APP_VERSION")
        or os.getenv("RENDER_GIT_COMMIT", "unknown")[:80],
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "level": "WARNING",
        "message": "OPS-001 test alert",
    }
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=float(os.getenv("OPS_ALERT_TIMEOUT_SECONDS", "3")),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(
            json.dumps(
                {"ok": False, "error_type": type(exc).__name__},
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps({"ok": True, "status_code": response.status_code}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
