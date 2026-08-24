from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\b"),
)


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in ("api_key", "apikey", "authorization", "secret", "token")):
                clean[str(key)] = "[REDACTED]"
            else:
                clean[str(key)] = redact_secrets(item)
        return clean
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        result = value
        for pattern in _SECRET_PATTERNS:
            if pattern.groups:
                result = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", result)
            else:
                result = pattern.sub("[REDACTED]", result)
        return result
    return value


def flatten_text(value: Any) -> str:
    parts: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                parts.append(str(key))
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)
        elif item is not None:
            parts.append(str(item))

    visit(value)
    return "\n".join(parts)


def normalize_text(value: str) -> str:
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"[^\w%+.#/-]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def get_path(value: Any, dotted_path: str) -> tuple[bool, Any]:
    current = value
    if dotted_path in ("", "$"):
        return True, current
    path = dotted_path[2:] if dotted_path.startswith("$.") else dotted_path
    for segment in path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return False, None
    return True, current


def iter_paths(value: Any, prefix: str = "$") -> Iterable[tuple[str, Any]]:
    yield prefix, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from iter_paths(item, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_paths(item, f"{prefix}[{index}]")
