"""Gunicorn configuration shared by Docker and the VPS test environment."""

from __future__ import annotations

import os


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


bind = f"0.0.0.0:{_int('PORT', 8000, 1, 65535)}"

# One worker is intentional until rate-limit storage and Trudvsem sync are moved
# to shared services. Threads provide concurrency without duplicating in-memory
# limiter buckets or background state.
workers = _int("GUNICORN_WORKERS", 1, 1, 4)
threads = _int("GUNICORN_THREADS", 4, 1, 16)
worker_class = "gthread"
timeout = _int("GUNICORN_TIMEOUT", 90, 30, 300)
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30, 10, 120)
keepalive = _int("GUNICORN_KEEPALIVE", 5, 1, 30)
max_requests = _int("GUNICORN_MAX_REQUESTS", 1000, 0, 100000)
max_requests_jitter = _int("GUNICORN_MAX_REQUESTS_JITTER", 100, 0, 10000)

# Application HTTP logs are emitted by observability.py in structured JSON.
# Gunicorn writes only process and error events to stdout/stderr.
accesslog = None
errorlog = "-"
capture_output = True
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info").strip().lower() or "info"

# The container port is expected to be reachable only through the local host or
# an internal reverse-proxy network. Override with a concrete CIDR/IP in HOST-001.
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
secure_scheme_headers = {
    "X-FORWARDED-PROTOCOL": "ssl",
    "X-FORWARDED-PROTO": "https",
    "X-FORWARDED-SSL": "on",
}

preload_app = False
