#!/usr/bin/env python3
"""Execute a command with Yandex Lockbox entries injected into its environment.

Secret values are held in process memory only. They are never printed or written
to a dotenv file by this helper.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request

_METADATA_URL = (
    "http://169.254.169.254/computeMetadata/v1/instance/"
    "service-accounts/default/token"
)
_PAYLOAD_URL = "https://payload.lockbox.api.cloud.yandex.net/lockbox/v1/secrets/{secret_id}/payload"
_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_MAX_VALUE = 65536


class SecretLoadError(RuntimeError):
    pass


def validate_database_url(value: str) -> None:
    """Fail closed if the Yandex PostgreSQL URL can weaken TLS/primary selection."""

    if not value:
        raise SecretLoadError("database_url_missing")
    try:
        parsed = urllib.parse.urlsplit(value)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    except ValueError as exc:
        raise SecretLoadError("database_url_invalid") from exc

    if not parsed.scheme.startswith("postgresql") or not parsed.hostname:
        raise SecretLoadError("database_url_invalid")

    required = {
        "sslmode": "verify-full",
        "sslrootcert": "/etc/ssl/certs/yandex-cloud-ca.pem",
        "target_session_attrs": "read-write",
    }
    for name, expected in required.items():
        values = query.get(name)
        if values != [expected]:
            raise SecretLoadError("database_url_security_parameters_invalid")


def _json_get(url: str, *, headers: dict[str, str], timeout: float = 5.0) -> dict:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(_MAX_VALUE * 20)
    except Exception as exc:
        raise SecretLoadError("secret_source_unavailable") from exc
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise SecretLoadError("secret_source_invalid_json") from exc
    if not isinstance(parsed, dict):
        raise SecretLoadError("secret_source_invalid_envelope")
    return parsed


def load_secret_entries(secret_id: str) -> dict[str, str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", secret_id or ""):
        raise SecretLoadError("invalid_secret_id")
    token_envelope = _json_get(
        _METADATA_URL,
        headers={"Metadata-Flavor": "Google"},
    )
    token = token_envelope.get("access_token")
    if not isinstance(token, str) or not token:
        raise SecretLoadError("iam_token_unavailable")
    payload = _json_get(
        _PAYLOAD_URL.format(secret_id=secret_id),
        headers={"Authorization": f"Bearer {token}"},
    )
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise SecretLoadError("secret_payload_invalid")
    result: dict[str, str] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise SecretLoadError("secret_entry_invalid")
        key = item.get("key")
        value = item.get("textValue")
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            raise SecretLoadError("secret_key_invalid")
        if not isinstance(value, str) or len(value) > _MAX_VALUE or "\x00" in value:
            raise SecretLoadError("secret_value_invalid")
        if key in result:
            raise SecretLoadError("secret_key_duplicate")
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--secret-id", default=os.environ.get("YC_LOCKBOX_SECRET_ID", ""))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("command is required after --")
    values = load_secret_entries(args.secret_id)
    environment = dict(os.environ)
    environment.update(values)
    validate_database_url(environment.get("DATABASE_URL", ""))
    os.execvpe(command[0], command, environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
