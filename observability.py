"""Operational observability for HTTP requests, providers, logs, and alerts.

OPS-001 keeps telemetry deliberately small and vendor-neutral.  Application
logs are written to stdout, request/provider metrics live in a bounded
in-process registry, and an optional HTTPS webhook can receive sanitised error
alerts.  The module never records request bodies, query strings, cookies,
OAuth tokens, resume text, or database credentials.
"""

from __future__ import annotations

import contextvars
import json
import logging
import queue
import re
import statistics
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

import requests
from flask import Flask, g, request

from config import AppSettings


_REQUEST_ID = contextvars.ContextVar("aca_request_id", default=None)
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_SECRET_KEY_RE = re.compile(
    r"(?i)(access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|"
    r"password|passwd|authorization|cookie|set-cookie|secret)"
    r"(\s*[=:]\s*)([^\s,;\]\}\)]+|\"[^\"]*\"|'[^']*')"
)
_QUERY_SECRET_RE = re.compile(
    r"(?i)([?&](?:access_token|refresh_token|api_key|key|token|secret|password)=)"
    r"([^&#\s]+)"
)
_URL_CREDENTIALS_RE = re.compile(r"(?i)(https?://[^/@:\s]+:)([^@/\s]+)(@)")
_URL_QUERY_RE = re.compile(r"(?i)(https?://[^?\s]+)\?[^\s]+")
_BEARER_RE = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_ALLOWED_LOG_FIELDS = {
    "event",
    "provider",
    "operation",
    "endpoint",
    "route",
    "method",
    "status_code",
    "status_class",
    "duration_ms",
    "result_count",
    "error_type",
    "database_revision",
    "expected_revision",
    "alert_delivery",
    "request_id",
}


def _utc_timestamp(epoch: float | None = None) -> str:
    value = time.time() if epoch is None else epoch
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="milliseconds")


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return round(ordered[0], 3)
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    value = ordered[lower] * (1 - weight) + ordered[upper] * weight
    return round(value, 3)


class LogSanitizer:
    """Remove configured secrets and common credential patterns from text."""

    def __init__(self, secret_values: Iterable[object] = ()) -> None:
        cleaned: list[str] = []
        for raw in secret_values:
            value = str(raw or "").strip()
            if len(value) >= 4 and value not in cleaned:
                cleaned.append(value)
        self._secret_values = tuple(sorted(cleaned, key=len, reverse=True))

    def redact_text(self, value: object, *, limit: int = 12_000) -> str:
        text = str(value)
        for secret in self._secret_values:
            text = text.replace(secret, "[REDACTED]")
        text = _URL_CREDENTIALS_RE.sub(r"\1[REDACTED]\3", text)
        # Request/provider query strings may contain job titles, regions, or
        # other user input. Operational logs keep only the URL origin/path.
        text = _URL_QUERY_RE.sub(r"\1?[QUERY_REDACTED]", text)
        text = _QUERY_SECRET_RE.sub(r"\1[REDACTED]", text)
        text = _BEARER_RE.sub(r"\1 [REDACTED]", text)
        text = _SECRET_KEY_RE.sub(r"\1\2[REDACTED]", text)
        if len(text) > limit:
            return text[:limit] + "...[truncated]"
        return text

    def redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                if _SECRET_KEY_RE.search(f"{key_text}=placeholder"):
                    sanitized[key_text] = "[REDACTED]"
                else:
                    sanitized[key_text] = self.redact(item)
            return sanitized
        if isinstance(value, tuple):
            return tuple(self.redact(item) for item in value)
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, (str, bytes)):
            return self.redact_text(value.decode(errors="replace") if isinstance(value, bytes) else value)
        return value


class SensitiveDataFilter(logging.Filter):
    """Sanitise a record before any formatter or alert handler sees it."""

    def __init__(self, sanitizer: LogSanitizer) -> None:
        super().__init__()
        self.sanitizer = sanitizer

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.sanitizer.redact(record.msg)
        record.args = self.sanitizer.redact(record.args)
        if not getattr(record, "request_id", None):
            record.request_id = current_request_id()
        for field_name in _ALLOWED_LOG_FIELDS:
            if hasattr(record, field_name):
                setattr(record, field_name, self.sanitizer.redact(getattr(record, field_name)))
        return True


class JsonLogFormatter(logging.Formatter):
    """Emit a single bounded JSON object per log record."""

    def __init__(
        self,
        *,
        sanitizer: LogSanitizer,
        service_name: str,
        environment: str,
        app_version: str,
    ) -> None:
        super().__init__()
        self.sanitizer = sanitizer
        self.service_name = service_name
        self.environment = environment
        self.app_version = app_version

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _utc_timestamp(record.created),
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "version": self.app_version,
            "logger": record.name,
            "message": self.sanitizer.redact_text(record.getMessage(), limit=4_000),
            "process_id": record.process,
            "thread": record.threadName,
        }
        request_id = getattr(record, "request_id", None) or current_request_id()
        if request_id:
            payload["request_id"] = request_id
        for field_name in _ALLOWED_LOG_FIELDS:
            value = getattr(record, field_name, None)
            if value is not None and field_name not in payload:
                payload[field_name] = self.sanitizer.redact(value)
        if record.exc_info:
            payload["error_type"] = payload.get("error_type") or record.exc_info[0].__name__
            payload["exception"] = self.sanitizer.redact_text(
                self.formatException(record.exc_info),
                limit=8_000,
            )
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


class TextLogFormatter(logging.Formatter):
    """Readable local formatter carrying the same correlation fields."""

    def __init__(self, sanitizer: LogSanitizer) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s")
        self.sanitizer = sanitizer

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        request_id = getattr(record, "request_id", None) or current_request_id()
        if request_id:
            base = f"{base} request_id={request_id}"
        return self.sanitizer.redact_text(base)


@dataclass
class _MetricBucket:
    calls: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    status_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    durations_ms: deque[float] = field(default_factory=lambda: deque(maxlen=300))
    last_duration_ms: float | None = None
    last_status_code: int | None = None
    last_error_type: str | None = None
    last_attempt_at: str | None = None
    last_success_at: str | None = None

    def snapshot(self) -> dict[str, Any]:
        durations = list(self.durations_ms)
        return {
            "calls": self.calls,
            "successes": self.successes,
            "failures": self.failures,
            "timeouts": self.timeouts,
            "status_counts": dict(sorted(self.status_counts.items())),
            "latency_ms": {
                "last": self.last_duration_ms,
                "average": round(statistics.fmean(durations), 3) if durations else None,
                "p50": _percentile(durations, 0.50),
                "p95": _percentile(durations, 0.95),
            },
            "last_status_code": self.last_status_code,
            "last_error_type": self.last_error_type,
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
        }


class OperationsState:
    """Bounded in-process telemetry used by diagnostics and future exporters."""

    def __init__(self) -> None:
        self.started_monotonic = time.monotonic()
        self.started_at = _utc_timestamp()
        self._lock = threading.RLock()
        self._http: dict[str, _MetricBucket] = defaultdict(_MetricBucket)
        self._providers: dict[str, dict[str, _MetricBucket]] = defaultdict(
            lambda: defaultdict(_MetricBucket)
        )
        self._recent_errors: deque[dict[str, Any]] = deque(maxlen=50)
        self._alert_state = {
            "configured": False,
            "sent": 0,
            "failed": 0,
            "dropped": 0,
            "last_sent_at": None,
            "last_failure_at": None,
        }
        self.service_name = "ai-career-agent"
        self.environment = "unknown"
        self.app_version = "unknown"
        self.sanitizer = LogSanitizer()

    def configure(self, settings: AppSettings, sanitizer: LogSanitizer) -> None:
        with self._lock:
            self.service_name = settings.service_name
            self.environment = settings.environment
            self.app_version = settings.app_version
            self.sanitizer = sanitizer
            self._alert_state["configured"] = bool(settings.ops_alert_webhook_url)

    @property
    def uptime_seconds(self) -> int:
        return max(0, int(time.monotonic() - self.started_monotonic))

    def record_http(
        self,
        *,
        endpoint: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        with self._lock:
            bucket = self._http[endpoint]
            bucket.calls += 1
            status_class = f"{int(status_code) // 100}xx"
            bucket.status_counts[status_class] += 1
            if status_code < 500:
                bucket.successes += 1
            else:
                bucket.failures += 1
            bucket.durations_ms.append(duration_ms)
            bucket.last_duration_ms = round(duration_ms, 3)
            bucket.last_status_code = int(status_code)
            bucket.last_attempt_at = _utc_timestamp()
            if status_code < 500:
                bucket.last_success_at = bucket.last_attempt_at

    def record_provider(
        self,
        *,
        provider: str,
        operation: str,
        success: bool,
        duration_ms: float,
        status_code: int | None = None,
        error_type: str | None = None,
        timeout: bool = False,
    ) -> None:
        with self._lock:
            bucket = self._providers[provider][operation]
            bucket.calls += 1
            bucket.successes += int(success)
            bucket.failures += int(not success)
            bucket.timeouts += int(timeout)
            bucket.durations_ms.append(duration_ms)
            bucket.last_duration_ms = round(duration_ms, 3)
            bucket.last_status_code = status_code
            bucket.last_error_type = error_type
            bucket.last_attempt_at = _utc_timestamp()
            if success:
                bucket.last_success_at = bucket.last_attempt_at
            status_key = str(status_code) if status_code is not None else ("ok" if success else "error")
            bucket.status_counts[status_key] += 1

    def record_error(self, record: logging.LogRecord) -> dict[str, Any]:
        error_type = getattr(record, "error_type", None)
        if not error_type and record.exc_info:
            error_type = record.exc_info[0].__name__
        item = {
            "timestamp": _utc_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", None) or "application_error",
            "message": self.sanitizer.redact_text(record.getMessage(), limit=600),
            "request_id": getattr(record, "request_id", None) or current_request_id(),
            "error_type": error_type,
        }
        with self._lock:
            self._recent_errors.append(item)
        return item

    def record_alert_delivery(self, *, success: bool, dropped: bool = False) -> None:
        now = _utc_timestamp()
        with self._lock:
            if dropped:
                self._alert_state["dropped"] += 1
                return
            if success:
                self._alert_state["sent"] += 1
                self._alert_state["last_sent_at"] = now
            else:
                self._alert_state["failed"] += 1
                self._alert_state["last_failure_at"] = now

    def snapshot(self, *, include_recent_errors: bool = True) -> dict[str, Any]:
        with self._lock:
            payload = {
                "service": self.service_name,
                "environment": self.environment,
                "version": self.app_version,
                "started_at": self.started_at,
                "uptime_seconds": self.uptime_seconds,
                "http": {
                    key: value.snapshot()
                    for key, value in sorted(self._http.items())
                },
                "providers": {
                    provider: {
                        operation: bucket.snapshot()
                        for operation, bucket in sorted(operations.items())
                    }
                    for provider, operations in sorted(self._providers.items())
                },
                "alerts": dict(self._alert_state),
            }
            if include_recent_errors:
                payload["recent_errors"] = list(self._recent_errors)
            return payload

    def reset_for_tests(self) -> None:
        with self._lock:
            self._http.clear()
            self._providers.clear()
            self._recent_errors.clear()
            configured = self._alert_state["configured"]
            self._alert_state = {
                "configured": configured,
                "sent": 0,
                "failed": 0,
                "dropped": 0,
                "last_sent_at": None,
                "last_failure_at": None,
            }


OPS_STATE = OperationsState()


class AlertDispatcher:
    """Bounded asynchronous HTTPS webhook sender for sanitised error alerts."""

    def __init__(self) -> None:
        self.url: str | None = None
        self.token: str | None = None
        self.timeout = 3.0
        self.minimum_level = logging.ERROR
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def configure(self, settings: AppSettings) -> None:
        self.url = settings.ops_alert_webhook_url
        self.token = settings.ops_alert_webhook_token
        self.timeout = settings.ops_alert_timeout_seconds
        self.minimum_level = getattr(logging, settings.ops_alert_min_level, logging.ERROR)

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AI-Career-Agent-Ops/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _start_worker(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._worker,
                name="ops-alert-dispatcher",
                daemon=True,
            )
            self._thread.start()

    def enqueue(self, payload: dict[str, Any]) -> bool:
        if not self.configured:
            return False
        self._start_worker()
        try:
            self._queue.put_nowait(payload)
            return True
        except queue.Full:
            OPS_STATE.record_alert_delivery(success=False, dropped=True)
            return False

    def send_now(self, payload: dict[str, Any]) -> bool:
        if not self.url:
            return False
        safe_payload = OPS_STATE.sanitizer.redact(payload)
        try:
            response = requests.post(
                self.url,
                json=safe_payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception:
            # Alert delivery must never terminate the background worker or
            # cascade into the application's error path. Delivery state is
            # intentionally recorded without echoing a URL, token, or body.
            OPS_STATE.record_alert_delivery(success=False)
            return False
        OPS_STATE.record_alert_delivery(success=True)
        return True

    def _worker(self) -> None:
        while True:
            payload = self._queue.get()
            try:
                self.send_now(payload)
            finally:
                self._queue.task_done()


ALERT_DISPATCHER = AlertDispatcher()


class OpsErrorHandler(logging.Handler):
    """Capture recent errors and enqueue optional external alerts."""

    def __init__(self, sanitizer: LogSanitizer) -> None:
        super().__init__(level=logging.ERROR)
        self.sanitizer = sanitizer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            item = OPS_STATE.record_error(record)
            if record.levelno >= ALERT_DISPATCHER.minimum_level:
                payload = {
                    "event": "ai_career_agent_error",
                    "service": OPS_STATE.service_name,
                    "environment": OPS_STATE.environment,
                    "version": OPS_STATE.app_version,
                    **item,
                }
                ALERT_DISPATCHER.enqueue(self.sanitizer.redact(payload))
        except Exception:
            # Logging must never bring down the application or recurse into itself.
            return


def _settings_secrets(settings: AppSettings) -> list[str]:
    names = (
        "flask_secret_key",
        "token_encryption_key",
        "superjob_client_secret",
        "hh_client_secret",
        "hh_app_token",
        "reed_api_key",
        "sync_secret",
        "diagnostics_secret",
        "database_url",
        "ops_alert_webhook_url",
        "ops_alert_webhook_token",
    )
    return [str(getattr(settings, name, "") or "") for name in names]


def configure_logging(settings: AppSettings) -> LogSanitizer:
    """Configure stdout logging and bounded operational error capture."""

    sanitizer = LogSanitizer(_settings_secrets(settings))
    OPS_STATE.configure(settings, sanitizer)
    ALERT_DISPATCHER.configure(settings)

    root = logging.getLogger()
    level = getattr(logging, settings.log_level, logging.INFO)
    root.setLevel(level)

    if not settings.is_test:
        for handler in list(root.handlers):
            root.removeHandler(handler)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.addFilter(SensitiveDataFilter(sanitizer))
        if settings.log_format == "json":
            stream_handler.setFormatter(
                JsonLogFormatter(
                    sanitizer=sanitizer,
                    service_name=settings.service_name,
                    environment=settings.environment,
                    app_version=settings.app_version,
                )
            )
        else:
            stream_handler.setFormatter(TextLogFormatter(sanitizer))
        root.addHandler(stream_handler)

        error_handler = OpsErrorHandler(sanitizer)
        error_handler.addFilter(SensitiveDataFilter(sanitizer))
        root.addHandler(error_handler)

    logging.captureWarnings(True)
    logging.getLogger("urllib3").setLevel(max(level, logging.WARNING))
    logging.getLogger("alembic").setLevel(max(level, logging.INFO))
    return sanitizer


def current_request_id() -> str | None:
    return _REQUEST_ID.get()


def _incoming_request_id() -> str:
    supplied = request.headers.get("X-Request-ID", "").strip()
    if supplied and _REQUEST_ID_RE.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


def init_observability(app: Flask, settings: AppSettings) -> None:
    """Attach request IDs, access logs, and HTTP metrics to Flask."""

    app.extensions["ops_state"] = OPS_STATE
    app.extensions["ops_alert_dispatcher"] = ALERT_DISPATCHER

    @app.before_request
    def begin_request_observation():
        request_id = _incoming_request_id()
        g.request_id = request_id
        g.request_started_monotonic = time.monotonic()
        g.request_id_token = _REQUEST_ID.set(request_id)

    @app.after_request
    def finish_request_observation(response):  # noqa: ANN001
        request_id = getattr(g, "request_id", None) or current_request_id() or uuid.uuid4().hex
        response.headers.setdefault("X-Request-ID", request_id)
        started = getattr(g, "request_started_monotonic", time.monotonic())
        duration_ms = max(0.0, (time.monotonic() - started) * 1000.0)
        endpoint = request.endpoint or "unmatched"
        route = request.url_rule.rule if request.url_rule is not None else "<unmatched>"
        OPS_STATE.record_http(
            endpoint=endpoint,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        level = logging.DEBUG if endpoint in {"health", "health_live", "health_ready"} and response.status_code < 500 else logging.INFO
        logging.getLogger("http.access").log(
            level,
            "HTTP request completed",
            extra={
                "event": "http_request_completed",
                "request_id": request_id,
                "method": request.method,
                "endpoint": endpoint,
                "route": route,
                "status_code": response.status_code,
                "status_class": f"{response.status_code // 100}xx",
                "duration_ms": round(duration_ms, 3),
            },
        )
        return response

    @app.teardown_request
    def clear_request_observation(_error):  # noqa: ANN001
        token = getattr(g, "request_id_token", None)
        if token is not None:
            try:
                _REQUEST_ID.reset(token)
            except (LookupError, RuntimeError, ValueError):
                pass


class ProviderObservation:
    def __init__(self, provider: str, operation: str) -> None:
        self.provider = provider
        self.operation = operation
        self.status_code: int | None = None
        self.result_count: int | None = None
        self.success = True
        self.error_type: str | None = None
        self.timeout = False

    def fail(self, error_type: str, *, status_code: int | None = None, timeout: bool = False) -> None:
        self.success = False
        self.error_type = str(error_type)[:120]
        self.status_code = status_code
        self.timeout = bool(timeout)


@contextmanager
def provider_operation(provider: str, operation: str):
    """Measure a provider call without recording arguments or payloads."""

    started = time.monotonic()
    observation = ProviderObservation(provider, operation)
    try:
        yield observation
    except Exception as exc:
        observation.fail(
            type(exc).__name__,
            status_code=getattr(getattr(exc, "response", None), "status_code", None),
            timeout=isinstance(exc, requests.Timeout),
        )
        raise
    finally:
        duration_ms = max(0.0, (time.monotonic() - started) * 1000.0)
        OPS_STATE.record_provider(
            provider=provider,
            operation=operation,
            success=observation.success,
            duration_ms=duration_ms,
            status_code=observation.status_code,
            error_type=observation.error_type,
            timeout=observation.timeout,
        )
        log_level = logging.INFO if observation.success else logging.WARNING
        logging.getLogger("provider.metrics").log(
            log_level,
            "Provider operation completed",
            extra={
                "event": "provider_operation_completed",
                "provider": provider,
                "operation": operation,
                "status_code": observation.status_code,
                "duration_ms": round(duration_ms, 3),
                "result_count": observation.result_count,
                "error_type": observation.error_type,
            },
        )


def build_test_alert_payload(message: str = "OPS-001 test alert") -> dict[str, Any]:
    return {
        "event": "ops_test_alert",
        "service": OPS_STATE.service_name,
        "environment": OPS_STATE.environment,
        "version": OPS_STATE.app_version,
        "timestamp": _utc_timestamp(),
        "level": "WARNING",
        "message": OPS_STATE.sanitizer.redact_text(message, limit=300),
        "request_id": current_request_id(),
    }
