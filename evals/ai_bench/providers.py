from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ProviderError
from .models import BenchmarkCase, ProviderResponse, ProviderSpec
from .util import redact_secrets


class ProviderAdapter(ABC):
    def __init__(self, spec: ProviderSpec, repo_root: Path, timeout_seconds: float) -> None:
        self.spec = spec
        self.repo_root = repo_root
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def invoke(self, case: BenchmarkCase, schema: dict[str, Any]) -> ProviderResponse:
        raise NotImplementedError


class FixtureProvider(ProviderAdapter):
    def __init__(self, spec: ProviderSpec, repo_root: Path, timeout_seconds: float) -> None:
        super().__init__(spec, repo_root, timeout_seconds)
        output_dir = spec.options.get("outputs_dir")
        if not isinstance(output_dir, str) or not output_dir.strip():
            raise ConfigurationError(f"{spec.provider_id}: fixture adapter requires outputs_dir")
        self.output_dir = (repo_root / output_dir).resolve()
        try:
            self.output_dir.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise ConfigurationError(f"{spec.provider_id}: outputs_dir must stay in repository") from exc

    def invoke(self, case: BenchmarkCase, schema: dict[str, Any]) -> ProviderResponse:
        path = self.output_dir / f"{case.case_id}.json"
        started = time.perf_counter()
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderError(f"{self.spec.provider_id}: cannot read fixture output for {case.case_id}: {exc}") from exc
        latency = (time.perf_counter() - started) * 1000.0
        return ProviderResponse(content=content, latency_ms=latency, metadata={"mode": "deterministic_fixture"})


class CommandProvider(ProviderAdapter):
    def __init__(self, spec: ProviderSpec, repo_root: Path, timeout_seconds: float) -> None:
        super().__init__(spec, repo_root, timeout_seconds)
        command = spec.options.get("command")
        if isinstance(command, str):
            command = shlex.split(command)
        if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
            raise ConfigurationError(f"{spec.provider_id}: command adapter requires a command string/list")
        self.command = command
        pass_env = spec.options.get("pass_env", [])
        if not isinstance(pass_env, list) or not all(isinstance(name, str) and name for name in pass_env):
            raise ConfigurationError(f"{spec.provider_id}: pass_env must be a list of environment variable names")
        self.pass_env = tuple(pass_env)

    def invoke(self, case: BenchmarkCase, schema: dict[str, Any]) -> ProviderResponse:
        payload = {
            "case_id": case.case_id,
            "task": case.task,
            "language": case.language,
            "messages": list(case.messages),
            "schema": schema,
        }
        env = {"PATH": os.environ.get("PATH", "")}
        for name in self.pass_env:
            if name in os.environ:
                env[name] = os.environ[name]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                self.command,
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                capture_output=True,
                cwd=self.repo_root,
                env=env,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderError(f"{self.spec.provider_id}: command invocation failed: {exc}") from exc
        latency = (time.perf_counter() - started) * 1000.0
        if completed.returncode != 0:
            safe_stderr = str(redact_secrets(completed.stderr.strip()))[:500]
            raise ProviderError(f"{self.spec.provider_id}: command exited {completed.returncode}: {safe_stderr}")
        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"{self.spec.provider_id}: command returned invalid JSON") from exc
        if isinstance(envelope, dict) and "content" in envelope:
            content = envelope["content"]
            usage = envelope.get("usage") or {}
            metadata = redact_secrets(envelope.get("metadata") or {})
        else:
            content = envelope
            usage = {}
            metadata = {}
        return ProviderResponse(
            content=content,
            latency_ms=latency,
            input_tokens=_optional_int(usage.get("input_tokens")),
            output_tokens=_optional_int(usage.get("output_tokens")),
            metadata=dict(metadata) if isinstance(metadata, dict) else {},
        )


class OpenAICompatibleProvider(ProviderAdapter):
    """Generic chat-completions adapter with an explicitly configured endpoint.

    This adapter is intentionally not wired into the production service. It is
    only an evaluation transport. Vendor-specific endpoint/model decisions are
    deferred to AI-PROVIDER-001.
    """

    def __init__(self, spec: ProviderSpec, repo_root: Path, timeout_seconds: float) -> None:
        super().__init__(spec, repo_root, timeout_seconds)
        endpoint = spec.options.get("endpoint")
        endpoint_env = spec.options.get("endpoint_env")
        if endpoint_env:
            endpoint = os.environ.get(str(endpoint_env), "")
        if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
            raise ConfigurationError(f"{spec.provider_id}: openai_compatible requires an explicit HTTPS endpoint or endpoint_env")
        self.endpoint = endpoint
        model = str(spec.options.get("model", "")).strip()
        model_env = str(spec.options.get("model_env", "")).strip()
        if model_env:
            model = os.environ.get(model_env, "").strip()
            if not model:
                raise ConfigurationError(f"{spec.provider_id}: model environment variable is not set")
        if not model:
            raise ConfigurationError(f"{spec.provider_id}: model or model_env is required")
        self.model = model
        self.metadata_model = str(spec.options.get("metadata_model", "")).strip() or self.model
        api_key_env = str(spec.options.get("api_key_env", "")).strip()
        if not api_key_env:
            raise ConfigurationError(f"{spec.provider_id}: api_key_env is required")
        self.api_key_env = api_key_env
        self.auth_scheme = str(spec.options.get("auth_scheme", "Bearer")).strip() or "Bearer"
        if self.auth_scheme not in {"Bearer", "Api-Key"}:
            raise ConfigurationError(f"{spec.provider_id}: auth_scheme must be Bearer or Api-Key")
        self.temperature = float(spec.options.get("temperature", 0.0))
        self.max_tokens = int(spec.options.get("max_tokens", 1600))
        self.response_format = spec.options.get("response_format", {"type": "json_object"})
        self.response_schema_mode = str(spec.options.get("response_schema_mode", "")).strip()
        if self.response_schema_mode not in {"", "json_schema"}:
            raise ConfigurationError(f"{spec.provider_id}: unsupported response_schema_mode")
        strict_option = spec.options.get("response_schema_strict")
        if strict_option is not None and not isinstance(strict_option, bool):
            raise ConfigurationError(f"{spec.provider_id}: response_schema_strict must be boolean")
        self.response_schema_strict = strict_option
        self.extra_headers_env = spec.options.get("extra_headers_env", {})
        if not isinstance(self.extra_headers_env, dict):
            raise ConfigurationError(f"{spec.provider_id}: extra_headers_env must be an object")

    def invoke(self, case: BenchmarkCase, schema: dict[str, Any]) -> ProviderResponse:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise ProviderError(f"{self.spec.provider_id}: required credential environment variable is not set")
        headers = {"Content-Type": "application/json", "Authorization": f"{self.auth_scheme} {api_key}"}
        for header_name, env_name in self.extra_headers_env.items():
            value = os.environ.get(str(env_name))
            if not value:
                raise ProviderError(f"{self.spec.provider_id}: required header environment variable is not set")
            headers[str(header_name)] = value
        body: dict[str, Any] = {
            "model": self.model,
            "messages": list(case.messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.response_schema_mode == "json_schema":
            schema_name = f"aca_{case.task}_{case.language}".replace("-", "_")[:64]
            json_schema = {
                "name": schema_name,
                "schema": schema,
            }
            if self.response_schema_strict is not None:
                json_schema["strict"] = self.response_schema_strict
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": json_schema,
            }
        elif self.response_format:
            body["response_format"] = self.response_format
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(4 * 1024 * 1024)
        except urllib.error.HTTPError as exc:
            safe_body = ""
            try:
                safe_body = str(redact_secrets(exc.read(2048).decode("utf-8", errors="replace")))
            except Exception:
                safe_body = ""
            raise ProviderError(f"{self.spec.provider_id}: HTTP {exc.code}: {safe_body[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError(f"{self.spec.provider_id}: transport failure: {type(exc).__name__}") from exc
        latency = (time.perf_counter() - started) * 1000.0
        try:
            envelope = json.loads(raw)
            message_content = envelope["choices"][0]["message"]["content"]
            content = json.loads(message_content) if isinstance(message_content, str) else message_content
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.spec.provider_id}: response is not a supported JSON chat-completions envelope") from exc
        usage = envelope.get("usage") or {}
        return ProviderResponse(
            content=content,
            latency_ms=latency,
            input_tokens=_optional_int(usage.get("prompt_tokens") or usage.get("input_tokens")),
            output_tokens=_optional_int(usage.get("completion_tokens") or usage.get("output_tokens")),
            metadata={"model": self.metadata_model, "mode": "live"},
        )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def create_provider(spec: ProviderSpec, repo_root: Path, timeout_seconds: float) -> ProviderAdapter:
    adapters = {
        "fixture": FixtureProvider,
        "command": CommandProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }
    adapter_class = adapters.get(spec.adapter)
    if adapter_class is None:
        raise ConfigurationError(f"{spec.provider_id}: unsupported adapter {spec.adapter!r}")
    return adapter_class(spec, repo_root, timeout_seconds)
