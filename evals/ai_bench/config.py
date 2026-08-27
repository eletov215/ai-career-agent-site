from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ConfigurationError
from .models import ProviderSpec


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "evals").is_dir() and ((candidate / "app.py").exists() or (candidate / "README.md").exists()):
            return candidate
    raise ConfigurationError(f"Cannot locate repository root from {start}")


def load_config(path: Path) -> tuple[dict[str, Any], Path, list[ProviderSpec]]:
    path = path.resolve()
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot read benchmark config {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise ConfigurationError("Benchmark config root must be an object")
    if str(config.get("benchmark_version", "")) != "1.3":
        raise ConfigurationError("benchmark_version must be '1.3'")

    repo_root = find_repo_root(path.parent)
    providers_raw = config.get("providers")
    if not isinstance(providers_raw, list) or not providers_raw:
        raise ConfigurationError("At least one provider must be configured")
    providers: list[ProviderSpec] = []
    seen: set[str] = set()
    for raw in providers_raw:
        if not isinstance(raw, dict):
            raise ConfigurationError("Each provider config must be an object")
        provider_id = str(raw.get("id", "")).strip()
        adapter = str(raw.get("adapter", "")).strip()
        if not provider_id or not adapter:
            raise ConfigurationError("Provider id and adapter are required")
        if provider_id in seen:
            raise ConfigurationError(f"Duplicate provider id: {provider_id}")
        seen.add(provider_id)
        providers.append(
            ProviderSpec(
                provider_id=provider_id,
                adapter=adapter,
                enabled=bool(raw.get("enabled", True)),
                options={key: value for key, value in raw.items() if key not in {"id", "adapter", "enabled"}},
            )
        )
    return config, repo_root, providers


def resolve_repo_path(repo_root: Path, value: str, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{label} must be a non-empty path")
    resolved = (repo_root / value).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ConfigurationError(f"{label} must stay inside the repository") from exc
    return resolved
