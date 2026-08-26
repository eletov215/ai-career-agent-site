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
    """Evaluation-only OpenAI-compatible chat-completions transport.

    The adapter records only bounded structural diagnostics. It never stores
    raw response bodies, request headers, credentials or refusal text. A
    provider may be retried at most once when explicitly configured, and only
    for transient HTTP/transport failures or malformed response envelopes.
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
        max_retries = spec.options.get("max_retries", 0)
        if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries not in {0, 1}:
            raise ConfigurationError(f"{spec.provider_id}: max_retries must be 0 or 1")
        self.max_retries = max_retries
        backoff = spec.options.get("retry_backoff_seconds", 0.5)
        if not isinstance(backoff, (int, float)) or isinstance(backoff, bool) or not 0 <= float(backoff) <= 5:
            raise ConfigurationError(f"{spec.provider_id}: retry_backoff_seconds must be between 0 and 5")
        self.retry_backoff_seconds = float(backoff)

    def _request_body(self, case: BenchmarkCase, schema: dict[str, Any]) -> bytes:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": list(case.messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.response_schema_mode == "json_schema":
            schema_name = f"aca_{case.task}_{case.language}".replace("-", "_")[:64]
            json_schema: dict[str, Any] = {"name": schema_name, "schema": schema}
            if self.response_schema_strict is not None:
                json_schema["strict"] = self.response_schema_strict
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}
        elif self.response_format:
            body["response_format"] = self.response_format
        return json.dumps(body, ensure_ascii=False).encode("utf-8")

    def _headers(self) -> dict[str, str]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise ProviderError(f"{self.spec.provider_id}: required credential environment variable is not set")
        headers = {"Content-Type": "application/json", "Authorization": f"{self.auth_scheme} {api_key}"}
        for header_name, env_name in self.extra_headers_env.items():
            value = os.environ.get(str(env_name))
            if not value:
                raise ProviderError(f"{self.spec.provider_id}: required header environment variable is not set")
            headers[str(header_name)] = value
        return headers

    @staticmethod
    def _base_diagnostics() -> dict[str, Any]:
        return {
            "http_status": None,
            "envelope_json_valid": None,
            "top_level_type": None,
            "choices_present": None,
            "message_present": None,
            "content_present": None,
            "content_type": None,
            "refusal_present": None,
            "finish_reason": None,
        }

    def _perform_request(self, request: urllib.request.Request) -> tuple[bytes, int | None]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(4 * 1024 * 1024)
                status = getattr(response, "status", None)
                return raw, int(status) if status is not None else 200
        except urllib.error.HTTPError as exc:
            code = int(exc.code)
            diagnostics = self._base_diagnostics()
            diagnostics.update(
                {
                    "http_status": code,
                    "reason": f"http_{code}",
                    "retryable": code == 429 or 500 <= code <= 599,
                }
            )
            raise ProviderError(f"{self.spec.provider_id}: HTTP {code}", diagnostics=diagnostics) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = "transport_timeout" if isinstance(exc, TimeoutError) or "timed out" in str(exc).casefold() else "transport_error"
            diagnostics = self._base_diagnostics()
            diagnostics.update({"reason": reason, "retryable": True})
            raise ProviderError(
                f"{self.spec.provider_id}: transport failure: {type(exc).__name__}",
                diagnostics=diagnostics,
            ) from exc

    def _decode_envelope(self, raw: bytes, http_status: int | None) -> tuple[Any, dict[str, Any], dict[str, Any]]:
        diagnostics = self._base_diagnostics()
        diagnostics["http_status"] = http_status
        try:
            envelope = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            diagnostics.update(
                {
                    "envelope_json_valid": False,
                    "top_level_type": "invalid_json",
                    "reason": "envelope_invalid_json",
                    "retryable": True,
                }
            )
            raise ProviderError(
                f"{self.spec.provider_id}: response envelope is not valid JSON",
                diagnostics=diagnostics,
            ) from exc

        diagnostics["envelope_json_valid"] = True
        diagnostics["top_level_type"] = type(envelope).__name__
        if not isinstance(envelope, dict):
            diagnostics.update({"reason": "envelope_not_object", "retryable": True})
            raise ProviderError(
                f"{self.spec.provider_id}: response envelope is not an object",
                diagnostics=diagnostics,
            )

        choices = envelope.get("choices")
        diagnostics["choices_present"] = isinstance(choices, list) and bool(choices)
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            diagnostics.update({"reason": "choices_missing", "retryable": True})
            raise ProviderError(
                f"{self.spec.provider_id}: response choices are missing",
                diagnostics=diagnostics,
            )

        choice = choices[0]
        diagnostics["finish_reason"] = str(choice.get("finish_reason")) if choice.get("finish_reason") is not None else None
        message = choice.get("message")
        diagnostics["message_present"] = isinstance(message, dict)
        if not isinstance(message, dict):
            diagnostics.update({"reason": "message_missing", "retryable": True})
            raise ProviderError(
                f"{self.spec.provider_id}: response message is missing",
                diagnostics=diagnostics,
            )

        refusal = message.get("refusal")
        diagnostics["refusal_present"] = bool(refusal)
        message_content = message.get("content")
        diagnostics["content_present"] = message_content is not None
        diagnostics["content_type"] = type(message_content).__name__ if message_content is not None else "null"

        if refusal:
            diagnostics.update({"reason": "model_refusal", "retryable": False})
            raise ProviderError(
                f"{self.spec.provider_id}: model returned a refusal",
                diagnostics=diagnostics,
            )
        if message_content is None:
            diagnostics.update({"reason": "content_null", "retryable": True})
            raise ProviderError(
                f"{self.spec.provider_id}: response content is null",
                diagnostics=diagnostics,
            )
        if isinstance(message_content, str):
            try:
                content = json.loads(message_content)
            except json.JSONDecodeError as exc:
                diagnostics.update({"reason": "content_invalid_json", "retryable": True})
                raise ProviderError(
                    f"{self.spec.provider_id}: response content is not valid JSON",
                    diagnostics=diagnostics,
                ) from exc
        elif isinstance(message_content, (dict, list)):
            content = message_content
        else:
            diagnostics.update({"reason": "content_unsupported_type", "retryable": True})
            raise ProviderError(
                f"{self.spec.provider_id}: response content has unsupported type",
                diagnostics=diagnostics,
            )

        usage = envelope.get("usage") or {}
        diagnostics.update({"reason": "ok", "retryable": False})
        return content, usage if isinstance(usage, dict) else {}, diagnostics

    def invoke(self, case: BenchmarkCase, schema: dict[str, Any]) -> ProviderResponse:
        request = urllib.request.Request(
            self.endpoint,
            data=self._request_body(case, schema),
            headers=self._headers(),
            method="POST",
        )
        started = time.perf_counter()
        retry_reasons: list[str] = []
        attempts = self.max_retries + 1
        last_error: ProviderError | None = None

        for attempt in range(1, attempts + 1):
            try:
                raw, status = self._perform_request(request)
                content, usage, diagnostics = self._decode_envelope(raw, status)
                latency = (time.perf_counter() - started) * 1000.0
                diagnostics = dict(diagnostics)
                diagnostics.update(
                    {
                        "attempt_count": attempt,
                        "retry_count": attempt - 1,
                        "retry_reasons": list(retry_reasons),
                    }
                )
                return ProviderResponse(
                    content=content,
                    latency_ms=latency,
                    input_tokens=_optional_int(usage.get("prompt_tokens") or usage.get("input_tokens")),
                    output_tokens=_optional_int(usage.get("completion_tokens") or usage.get("output_tokens")),
                    metadata={
                        "model": self.metadata_model,
                        "mode": "live",
                        "provider_diagnostics": diagnostics,
                    },
                )
            except ProviderError as exc:
                last_error = exc
                diagnostics = dict(exc.diagnostics)
                reason = str(diagnostics.get("reason") or "provider_error")
                retryable = bool(diagnostics.get("retryable"))
                if attempt < attempts and retryable:
                    retry_reasons.append(reason)
                    if self.retry_backoff_seconds:
                        time.sleep(self.retry_backoff_seconds)
                    continue
                diagnostics.update(
                    {
                        "attempt_count": attempt,
                        "retry_count": attempt - 1,
                        "retry_reasons": list(retry_reasons),
                    }
                )
                raise ProviderError(str(exc), diagnostics=diagnostics) from exc

        # Defensive fallback: the loop always returns or raises.
        raise last_error or ProviderError(f"{self.spec.provider_id}: provider invocation failed")


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
