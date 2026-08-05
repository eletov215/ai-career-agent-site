"""Application security controls for sessions, CSRF, limits, and responses.

The module intentionally keeps security policy separate from business routes so
future blueprints, background workers, and a custom domain can reuse the same
configuration.  The controls are enabled in production by default and are
covered by route tests.
"""

from __future__ import annotations

import logging
import secrets

from flask import Flask, g, jsonify, make_response, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.exceptions import RequestEntityTooLarge, SecurityError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import AppSettings

logger = logging.getLogger(__name__)

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_UPLOAD_ENDPOINTS = {"resume_preview_api", "ai_career"}
_JSON_LIMIT_ENDPOINTS = {"university_logo_api"}


def _wants_json() -> bool:
    if request.path.startswith(("/api/", "/sync/")):
        return True
    if request.is_json:
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json" and (
        request.accept_mimetypes["application/json"]
        > request.accept_mimetypes["text/html"]
    )


def _error_response(*, title: str, message: str, status: int):
    if _wants_json():
        response = jsonify({"ok": False, "error": message})
        response.status_code = status
        return response
    return make_response(
        render_template(
            "message.html",
            success=False,
            title=title,
            message=message,
        ),
        status,
    )


def _request_nonce() -> str:
    nonce = getattr(g, "csp_nonce", None)
    if not nonce:
        nonce = secrets.token_urlsafe(18)
        g.csp_nonce = nonce
    return nonce


def _content_security_policy(settings: AppSettings, nonce: str) -> str:
    directives = [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        f"script-src 'self' 'nonce-{nonce}' https://cdnjs.cloudflare.com",
        "script-src-attr 'none'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob:",
        "connect-src 'self'",
        "media-src 'none'",
        "frame-src 'none'",
        "worker-src 'self' blob:",
        "manifest-src 'self'",
    ]
    if settings.is_production:
        directives.append("upgrade-insecure-requests")
    return "; ".join(directives)


def _copy_rate_limit_headers(source, target) -> None:  # noqa: ANN001
    for name in (
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ):
        value = source.headers.get(name)
        if value:
            target.headers[name] = value


def init_security(app: Flask, settings: AppSettings) -> None:
    """Attach the SEC-001 controls to a configured Flask application."""

    if settings.trust_proxy_headers:
        # Render terminates TLS and forwards the original client/protocol.
        # Trust exactly one platform proxy and do not trust forwarded host.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.before_request
    def apply_request_resource_limits():
        _request_nonce()
        request.max_form_memory_size = settings.max_form_memory_size
        request.max_form_parts = settings.max_form_parts
        if request.method not in _UNSAFE_METHODS:
            return None
        if request.endpoint in _UPLOAD_ENDPOINTS:
            request.max_content_length = app.config["MAX_CONTENT_LENGTH"]
        elif request.endpoint in _JSON_LIMIT_ENDPOINTS:
            request.max_content_length = 32 * 1024
        else:
            request.max_content_length = 256 * 1024
        return None

    csrf.init_app(app)
    limiter.init_app(app)
    if (
        settings.is_production
        and settings.rate_limit_enabled
        and settings.rate_limit_storage_uri == "memory://"
    ):
        logger.warning(
            "Rate limiting uses per-process memory storage; configure a shared "
            "backend before scaling Gunicorn beyond one worker."
        )

    @app.context_processor
    def security_template_context():
        return {"csp_nonce": _request_nonce()}

    if settings.security_headers_enabled:

        @app.after_request
        def add_security_headers(response):  # noqa: ANN001
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.headers.setdefault(
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
            )
            response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
            response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
            response.headers.setdefault("Origin-Agent-Cluster", "?1")
            response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
            response.headers.setdefault("X-XSS-Protection", "0")
            response.headers.setdefault(
                "Content-Security-Policy",
                _content_security_policy(
                    settings,
                    _request_nonce(),
                ),
            )
            if settings.is_production and request.is_secure and settings.hsts_seconds:
                response.headers.setdefault(
                    "Strict-Transport-Security",
                    f"max-age={settings.hsts_seconds}; includeSubDomains",
                )
            if request.endpoint != "static":
                response.headers.setdefault("Cache-Control", "no-store, max-age=0")
                response.headers.setdefault("Pragma", "no-cache")
            return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):
        logger.warning(
            "CSRF validation rejected method=%s path=%s reason=%s",
            request.method,
            request.path,
            error.description,
        )
        return _error_response(
            title="Сессия формы устарела",
            message="Обновите страницу и повторите действие.",
            status=400,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(_error: RequestEntityTooLarge):
        return _error_response(
            title="Файл или запрос слишком большой",
            message="Уменьшите размер данных и повторите действие.",
            status=413,
        )

    @app.errorhandler(SecurityError)
    def handle_invalid_host(_error: SecurityError):
        return _error_response(
            title="Некорректный запрос",
            message="Адрес запроса не разрешён для этого сервиса.",
            status=400,
        )

    @app.errorhandler(429)
    def handle_rate_limit(error):  # noqa: ANN001
        original = error.get_response()
        response = _error_response(
            title="Слишком много запросов",
            message="Подождите немного и повторите действие.",
            status=429,
        )
        _copy_rate_limit_headers(original, response)
        return response

    @app.errorhandler(500)
    def handle_internal_error(error):  # noqa: ANN001
        original = getattr(error, "original_exception", None) or error
        logger.error(
            "Unhandled application error",
            exc_info=(type(original), original, original.__traceback__),
        )
        return _error_response(
            title="Временная ошибка сервиса",
            message="Повторите действие позже.",
            status=500,
        )


def diagnostics_access_allowed(settings: AppSettings) -> bool:
    """Return True only for explicitly enabled, secret-authenticated diagnostics."""

    if not settings.debug_diagnostics or not settings.diagnostics_secret:
        return False
    supplied = request.headers.get("X-Diagnostics-Secret", "").strip()
    return bool(supplied) and secrets.compare_digest(
        settings.diagnostics_secret,
        supplied,
    )
