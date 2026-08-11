"""Central application configuration for development, test, and production.

The module reads environment variables in one place and returns an immutable
``AppSettings`` object. Production and development never receive built-in
secrets. Deterministic placeholder credentials exist only for the test mode so
that the test suite can import the Flask application without real API keys.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from cryptography.fernet import Fernet


class ConfigurationError(RuntimeError):
    """Raised when application settings are missing or invalid."""


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_ENV_ALIASES = {
    "prod": "production",
    "production": "production",
    "dev": "development",
    "development": "development",
    "test": "test",
    "testing": "test",
}
_REQUIRED_SECRET_NAMES = (
    "FLASK_SECRET_KEY",
    "TOKEN_ENCRYPTION_KEY",
    "SUPERJOB_CLIENT_ID",
    "SUPERJOB_CLIENT_SECRET",
    "SUPERJOB_REDIRECT_URI",
    "HH_CLIENT_ID",
    "HH_CLIENT_SECRET",
    "HH_REDIRECT_URI",
    "HH_USER_AGENT",
)
_TEST_DEFAULTS = {
    "FLASK_SECRET_KEY": "test-only-flask-secret",
    "TOKEN_ENCRYPTION_KEY": "yPWPkxw3j4ZWDVBQ-i3kryGBFjd-5Bjg2tDjCNUMciw=",
    "SUPERJOB_CLIENT_ID": "test-superjob-client",
    "SUPERJOB_CLIENT_SECRET": "test-superjob-secret",
    "SUPERJOB_REDIRECT_URI": "http://localhost/oauth/superjob/callback",
    "HH_CLIENT_ID": "test-hh-client",
    "HH_CLIENT_SECRET": "test-hh-secret",
    "HH_REDIRECT_URI": "http://localhost/oauth/hh/callback",
    "HH_USER_AGENT": "AI-Career-Agent-Test/1.0 (tests@example.invalid)",
    "SYNC_SECRET": "test-sync-secret",
    "DIAGNOSTICS_SECRET": "test-diagnostics-secret",
}


def _clean(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def _optional(source: Mapping[str, str], name: str, default: str = "") -> str | None:
    value = _clean(source.get(name, default))
    return value or None


def _csv(source: Mapping[str, str], name: str) -> tuple[str, ...]:
    raw = _clean(source.get(name))
    if not raw:
        return ()
    values: list[str] = []
    for item in raw.split(","):
        value = item.strip()
        if value and value not in values:
            values.append(value)
    return tuple(values)


def _choice(
    source: Mapping[str, str],
    name: str,
    default: str,
    *,
    choices: set[str],
) -> str:
    value = _clean(source.get(name, default)) or default
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise ConfigurationError(
            f"Некорректное значение {name}={value!r}. Разрешены: {allowed}."
        )
    return value


def _validated_redirect_uri(
    name: str,
    value: str,
    *,
    environment: str,
) -> str:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError(
            f"{name} имеет некорректный URL."
        ) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ConfigurationError(
            f"{name} должен быть абсолютным HTTP(S) callback URL без credentials и fragment."
        )
    if environment == "production" and parsed.scheme != "https":
        raise ConfigurationError(
            f"{name} в production должен использовать HTTPS."
        )
    if port is not None and not (1 <= port <= 65535):
        raise ConfigurationError(f"{name} содержит недопустимый port.")
    return value



def _validated_optional_url(
    source: Mapping[str, str],
    name: str,
    *,
    environment: str,
) -> str | None:
    value = _optional(source, name)
    if not value:
        return None
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError(f"{name} имеет некорректный URL.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ConfigurationError(
            f"{name} должен быть абсолютным HTTP(S) URL без credentials и fragment."
        )
    if environment == "production" and parsed.scheme != "https":
        raise ConfigurationError(f"{name} в production должен использовать HTTPS.")
    if port is not None and not (1 <= port <= 65535):
        raise ConfigurationError(f"{name} содержит недопустимый port.")
    return value


def _validated_optional_email(source: Mapping[str, str], name: str) -> str | None:
    value = _optional(source, name)
    if not value:
        return None
    if len(value) > 254 or value.count("@") != 1 or any(ch.isspace() for ch in value):
        raise ConfigurationError(f"{name} должен содержать корректный email-адрес.")
    local, domain = value.rsplit("@", 1)
    if not local or not domain or "." not in domain:
        raise ConfigurationError(f"{name} должен содержать корректный email-адрес.")
    return value


def _service_name(source: Mapping[str, str]) -> str:
    value = _clean(source.get("SERVICE_NAME", "ai-career-agent")) or "ai-career-agent"
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,80}", value):
        raise ConfigurationError(
            "SERVICE_NAME должен содержать только буквы, цифры, точку, подчёркивание и дефис."
        )
    return value


def _app_version(source: Mapping[str, str]) -> str:
    value = _clean(source.get("APP_VERSION")) or _clean(source.get("RENDER_GIT_COMMIT")) or "development"
    if len(value) > 80:
        value = value[:80]
    return value

def _hostname_from_url(value: str) -> str | None:
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    hostname = (parsed.hostname or "").strip().lower()
    return hostname or None


def _trusted_hosts(
    source: Mapping[str, str],
    *,
    environment: str,
    redirect_uris: tuple[str, ...],
) -> tuple[str, ...]:
    hosts = list(_csv(source, "TRUSTED_HOSTS"))
    render_hostname = _clean(source.get("RENDER_EXTERNAL_HOSTNAME"))
    if render_hostname and render_hostname not in hosts:
        hosts.append(render_hostname)
    for redirect_uri in redirect_uris:
        hostname = _hostname_from_url(redirect_uri)
        if hostname and hostname not in hosts:
            hosts.append(hostname)
    if environment in {"development", "test"}:
        for hostname in ("localhost", "127.0.0.1", "::1"):
            if hostname not in hosts:
                hosts.append(hostname)
    if environment == "production" and not hosts:
        raise ConfigurationError(
            "Не удалось определить TRUSTED_HOSTS. Укажите TRUSTED_HOSTS или корректные OAuth redirect URI."
        )
    return tuple(hosts)


def _required(source: Mapping[str, str], name: str) -> str:
    value = _clean(source.get(name))
    if not value:
        raise ConfigurationError(f"Отсутствует обязательная переменная окружения: {name}.")
    return value


def _bool(source: Mapping[str, str], name: str, default: bool) -> bool:
    raw = _clean(source.get(name))
    if not raw:
        return default
    normalized = raw.casefold()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ConfigurationError(
        f"Некорректное значение {name}={raw!r}. Используйте true/false, 1/0, yes/no или on/off."
    )


def _int(
    source: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = _clean(source.get(name))
    if not raw:
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"Некорректное значение {name}={raw!r}: требуется целое число."
            ) from exc
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"Значение {name} не может быть меньше {minimum}.")
    if maximum is not None and value > maximum:
        raise ConfigurationError(f"Значение {name} не может быть больше {maximum}.")
    return value


def _float(
    source: Mapping[str, str],
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw = _clean(source.get(name))
    if not raw:
        value = default
    else:
        try:
            value = float(raw)
        except ValueError as exc:
            raise ConfigurationError(
                f"Некорректное значение {name}={raw!r}: требуется число."
            ) from exc
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"Значение {name} не может быть меньше {minimum}.")
    if maximum is not None and value > maximum:
        raise ConfigurationError(f"Значение {name} не может быть больше {maximum}.")
    return value


def _environment_name(source: Mapping[str, str]) -> str:
    raw = _clean(source.get("APP_ENV", "production")).casefold()
    environment = _ENV_ALIASES.get(raw)
    if environment is None:
        supported = ", ".join(sorted({"development", "production", "test"}))
        raise ConfigurationError(
            f"Некорректное значение APP_ENV={raw!r}. Поддерживаются: {supported}."
        )
    return environment


def _database_url(
    source: Mapping[str, str],
    *,
    environment: str,
    data_dir_raw: str,
) -> tuple[str, bool]:
    """Return a normalized SQLAlchemy URL and whether it was explicitly set."""

    raw = _clean(source.get("DATABASE_URL"))
    explicit = bool(raw)
    if raw.startswith("postgres://"):
        raw = "postgresql+psycopg://" + raw[len("postgres://") :]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+psycopg://" + raw[len("postgresql://") :]
    elif raw.startswith("postgresql+psycopg2://"):
        raw = "postgresql+psycopg://" + raw[len("postgresql+psycopg2://") :]

    if not raw:
        sqlite_path = (Path(data_dir_raw).expanduser() / "app.db").resolve()
        raw = f"sqlite:///{sqlite_path.as_posix()}"

    supported_prefixes = ("sqlite:", "postgresql+psycopg:")
    if not raw.startswith(supported_prefixes):
        raise ConfigurationError(
            "DATABASE_URL использует неподдерживаемый драйвер. "
            "Разрешены SQLite и PostgreSQL через psycopg 3."
        )

    if environment == "test" and raw.startswith("postgresql"):
        # Tests may opt into PostgreSQL explicitly, but the default remains an
        # isolated SQLite database under the per-session DATA_DIR.
        return raw, explicit
    return raw, explicit


def load_database_url(
    environ: Mapping[str, str] | None = None,
) -> tuple[str, bool]:
    """Load only database settings without requiring OAuth credentials.

    Alembic and maintenance scripts use this lightweight loader so database
    operations remain possible even before the Flask application is started.
    """

    source = dict(os.environ if environ is None else environ)
    environment = _environment_name(source)
    default_data_dir = (
        "/tmp/ai-career-agent-tests"
        if environment == "test"
        else "/tmp/ai-career-agent"
    )
    data_dir_raw = _clean(source.get("DATA_DIR", default_data_dir)) or default_data_dir
    return _database_url(
        source,
        environment=environment,
        data_dir_raw=data_dir_raw,
    )


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Validated runtime settings used by the Flask application."""

    environment: str
    flask_secret_key: str
    token_encryption_key: str
    superjob_client_id: str
    superjob_client_secret: str
    superjob_redirect_uri: str
    hh_client_id: str
    hh_client_secret: str
    hh_redirect_uri: str
    hh_user_agent: str
    hh_app_token: str | None
    reed_api_key: str | None
    sync_secret: str | None
    data_dir: Path
    database_url: str
    database_url_explicit: bool
    vacancy_cache_ttl: int
    vacancy_page_size: int
    search_page_size: int
    search_snapshot_ttl_seconds: int
    search_snapshot_max_candidates: int
    search_snapshot_max_pages_per_source: int
    search_snapshot_max_rounds_per_request: int
    search_snapshot_buffer_items: int
    search_snapshot_extension_lease_seconds: int
    trudvsem_sync_interval: int
    trudvsem_sync_items: int
    trudvsem_sync_batch: int
    trudvsem_request_attempts: int
    trudvsem_retry_backoff: float
    trudvsem_sync_enabled: bool
    trudvsem_sync_poll_seconds: int
    trudvsem_sync_stale_seconds: int
    trudvsem_worker_heartbeat_seconds: int
    trudvsem_sync_watermark_overlap_seconds: int
    trudvsem_vacancy_ttl_days: int
    trudvsem_closed_retention_days: int
    trudvsem_retry_base_seconds: int
    trudvsem_retry_max_seconds: int
    debug_hh: bool
    hh_currency_scan_pages: int
    max_resume_upload_mb: int
    max_resume_pages: int
    max_resume_text_characters: int
    session_cookie_secure: bool
    session_cookie_samesite: str
    session_lifetime_seconds: int
    auth_session_ttl_seconds: int
    auth_verification_ttl_seconds: int
    auth_reset_ttl_seconds: int
    auth_password_min_length: int
    auth_email_backend: str
    auth_email_from: str | None
    auth_email_from_name: str
    auth_smtp_host: str | None
    auth_smtp_port: int
    auth_smtp_username: str | None
    auth_smtp_password: str | None
    auth_smtp_use_tls: bool
    auth_smtp_use_ssl: bool
    auth_smtp_timeout_seconds: float
    csrf_enabled: bool
    csrf_time_limit_seconds: int
    rate_limit_enabled: bool
    rate_limit_storage_uri: str
    trusted_hosts: tuple[str, ...]
    trust_proxy_headers: bool
    security_headers_enabled: bool
    hsts_seconds: int
    max_form_memory_size: int
    max_form_parts: int
    debug_diagnostics: bool
    diagnostics_secret: str | None
    service_name: str
    app_version: str
    log_level: str
    log_format: str
    ops_alert_webhook_url: str | None
    ops_alert_webhook_token: str | None
    ops_alert_timeout_seconds: float
    ops_alert_min_level: str
    render_region: str
    port: int
    flask_debug: bool

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def flask_mapping(self) -> dict[str, object]:
        """Return the subset consumed directly by Flask."""

        return {
            "APP_ENV": self.environment,
            "TESTING": self.is_test,
            "DEBUG": self.flask_debug,
            "SECRET_KEY": self.flask_secret_key,
            "SESSION_COOKIE_NAME": "aca_session",
            "SESSION_COOKIE_SECURE": self.session_cookie_secure,
            "SESSION_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": self.session_cookie_samesite,
            "SESSION_COOKIE_PARTITIONED": False,
            "SESSION_REFRESH_EACH_REQUEST": False,
            "PERMANENT_SESSION_LIFETIME": timedelta(
                seconds=self.session_lifetime_seconds
            ),
            "PREFERRED_URL_SCHEME": "https" if self.is_production else "http",
            "TRUSTED_HOSTS": list(self.trusted_hosts),
            "WTF_CSRF_ENABLED": self.csrf_enabled,
            # Flask-WTF 1.3 expects the CSRF max age as an integer number
            # of seconds. Passing datetime.timedelta reaches itsdangerous
            # unchanged and raises a TypeError during token validation.
            "WTF_CSRF_TIME_LIMIT": self.csrf_time_limit_seconds,
            "WTF_CSRF_HEADERS": ["X-CSRFToken", "X-CSRF-Token"],
            "WTF_CSRF_METHODS": {"POST", "PUT", "PATCH", "DELETE"},
            "WTF_CSRF_SSL_STRICT": self.is_production,
            "RATELIMIT_ENABLED": self.rate_limit_enabled,
            "RATELIMIT_STORAGE_URI": self.rate_limit_storage_uri,
            "RATELIMIT_HEADERS_ENABLED": True,
            "RATELIMIT_KEY_PREFIX": "ai-career-agent",
            "TRUST_PROXY_HEADERS": self.trust_proxy_headers,
            "MAX_CONTENT_LENGTH": (
                self.max_resume_upload_mb * 1024 * 1024 + 1024 * 1024
            ),
            "MAX_FORM_MEMORY_SIZE": self.max_form_memory_size,
            "MAX_FORM_PARTS": self.max_form_parts,
        }


def load_settings(environ: Mapping[str, str] | None = None) -> AppSettings:
    """Load and validate settings from an environment mapping.

    ``APP_ENV`` defaults to ``production`` for backwards compatibility with
    the existing Render service. Test-only placeholder secrets are injected
    only when ``APP_ENV=test``. Production and development require explicit
    values for every secret and OAuth setting.
    """

    source = dict(os.environ if environ is None else environ)
    environment = _environment_name(source)

    if environment == "test":
        merged = dict(_TEST_DEFAULTS)
        merged.update(source)
        source = merged
    else:
        missing = [name for name in _REQUIRED_SECRET_NAMES if not _clean(source.get(name))]
        if missing:
            names = ", ".join(missing)
            location = "Render -> Environment" if environment == "production" else "локальное окружение"
            raise ConfigurationError(
                f"Ошибка конфигурации ({environment}). Отсутствуют обязательные переменные: "
                f"{names}. Добавьте их в {location}."
            )

    token_encryption_key = _required(source, "TOKEN_ENCRYPTION_KEY")
    try:
        Fernet(token_encryption_key.encode("ascii"))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ConfigurationError(
            "TOKEN_ENCRYPTION_KEY имеет неверный формат. Используйте ключ Fernet."
        ) from exc

    default_data_dir = "/tmp/ai-career-agent-tests" if environment == "test" else "/tmp/ai-career-agent"
    data_dir_raw = _clean(source.get("DATA_DIR", default_data_dir)) or default_data_dir

    flask_debug_default = environment == "development"
    sync_enabled_default = environment != "test"

    database_url_raw, database_url_explicit = _database_url(
        source,
        environment=environment,
        data_dir_raw=data_dir_raw,
    )

    session_cookie_secure = _bool(
        source,
        "SESSION_COOKIE_SECURE",
        environment == "production",
    )
    session_cookie_samesite = _choice(
        source,
        "SESSION_COOKIE_SAMESITE",
        "Lax",
        choices={"Lax", "Strict"},
    )
    csrf_enabled = _bool(source, "CSRF_ENABLED", True)
    rate_limit_enabled = _bool(source, "RATE_LIMIT_ENABLED", True)
    security_headers_enabled = _bool(source, "SECURITY_HEADERS_ENABLED", True)
    debug_diagnostics = _bool(source, "DEBUG_DIAGNOSTICS", False)
    diagnostics_secret = _optional(source, "DIAGNOSTICS_SECRET")

    if environment == "production":
        insecure_controls = []
        if not session_cookie_secure:
            insecure_controls.append("SESSION_COOKIE_SECURE")
        if not csrf_enabled:
            insecure_controls.append("CSRF_ENABLED")
        if not rate_limit_enabled:
            insecure_controls.append("RATE_LIMIT_ENABLED")
        if not security_headers_enabled:
            insecure_controls.append("SECURITY_HEADERS_ENABLED")
        if session_cookie_samesite != "Lax":
            insecure_controls.append("SESSION_COOKIE_SAMESITE=Lax")
        if insecure_controls:
            raise ConfigurationError(
                "Production не может запускаться с отключёнными контролями безопасности: "
                + ", ".join(insecure_controls)
                + "."
            )

    if debug_diagnostics and not diagnostics_secret:
        raise ConfigurationError(
            "DEBUG_DIAGNOSTICS требует DIAGNOSTICS_SECRET."
        )

    auth_email_backend = _choice(
        {**source, "AUTH_EMAIL_BACKEND": _clean(source.get("AUTH_EMAIL_BACKEND", "memory" if environment == "test" else "disabled")).lower()},
        "AUTH_EMAIL_BACKEND",
        "memory" if environment == "test" else "disabled",
        choices={"disabled", "memory", "smtp"},
    )
    if environment == "production" and auth_email_backend == "memory":
        raise ConfigurationError("AUTH_EMAIL_BACKEND=memory запрещён в production.")
    auth_email_from = _validated_optional_email(source, "AUTH_EMAIL_FROM")
    auth_smtp_host = _optional(source, "AUTH_SMTP_HOST")
    auth_smtp_username = _optional(source, "AUTH_SMTP_USERNAME")
    auth_smtp_password = _optional(source, "AUTH_SMTP_PASSWORD")
    auth_smtp_use_tls = _bool(source, "AUTH_SMTP_USE_TLS", True)
    auth_smtp_use_ssl = _bool(source, "AUTH_SMTP_USE_SSL", False)
    if auth_email_backend == "smtp":
        missing_auth_email = []
        if not auth_email_from:
            missing_auth_email.append("AUTH_EMAIL_FROM")
        if not auth_smtp_host:
            missing_auth_email.append("AUTH_SMTP_HOST")
        if auth_smtp_username and not auth_smtp_password:
            missing_auth_email.append("AUTH_SMTP_PASSWORD")
        if auth_smtp_password and not auth_smtp_username:
            missing_auth_email.append("AUTH_SMTP_USERNAME")
        if missing_auth_email:
            raise ConfigurationError(
                "AUTH_EMAIL_BACKEND=smtp требует: " + ", ".join(missing_auth_email) + "."
            )
        if auth_smtp_use_tls and auth_smtp_use_ssl:
            raise ConfigurationError(
                "AUTH_SMTP_USE_TLS и AUTH_SMTP_USE_SSL нельзя включать одновременно."
            )
        if environment == "production" and not (auth_smtp_use_tls or auth_smtp_use_ssl):
            raise ConfigurationError(
                "Для SMTP в production требуется защищённый режим: "
                "AUTH_SMTP_USE_TLS=1 или AUTH_SMTP_USE_SSL=1."
            )

    superjob_redirect_uri = _validated_redirect_uri(
        "SUPERJOB_REDIRECT_URI",
        _required(source, "SUPERJOB_REDIRECT_URI"),
        environment=environment,
    )
    hh_redirect_uri = _validated_redirect_uri(
        "HH_REDIRECT_URI",
        _required(source, "HH_REDIRECT_URI"),
        environment=environment,
    )
    trusted_hosts = _trusted_hosts(
        source,
        environment=environment,
        redirect_uris=(superjob_redirect_uri, hh_redirect_uri),
    )
    ops_alert_webhook_url = _validated_optional_url(
        source,
        "OPS_ALERT_WEBHOOK_URL",
        environment=environment,
    )
    trudvsem_retry_base_seconds = _int(
        source,
        "TRUDVSEM_RETRY_BASE_SECONDS",
        60,
        minimum=5,
        maximum=3600,
    )
    trudvsem_retry_max_seconds = _int(
        source,
        "TRUDVSEM_RETRY_MAX_SECONDS",
        3600,
        minimum=30,
        maximum=86_400,
    )
    if trudvsem_retry_max_seconds < trudvsem_retry_base_seconds:
        raise ConfigurationError(
            "TRUDVSEM_RETRY_MAX_SECONDS не может быть меньше "
            "TRUDVSEM_RETRY_BASE_SECONDS."
        )

    return AppSettings(
        environment=environment,
        flask_secret_key=_required(source, "FLASK_SECRET_KEY"),
        token_encryption_key=token_encryption_key,
        superjob_client_id=_required(source, "SUPERJOB_CLIENT_ID"),
        superjob_client_secret=_required(source, "SUPERJOB_CLIENT_SECRET"),
        superjob_redirect_uri=superjob_redirect_uri,
        hh_client_id=_required(source, "HH_CLIENT_ID"),
        hh_client_secret=_required(source, "HH_CLIENT_SECRET"),
        hh_redirect_uri=hh_redirect_uri,
        hh_user_agent=_required(source, "HH_USER_AGENT"),
        hh_app_token=_optional(source, "HH_APP_TOKEN"),
        reed_api_key=_optional(source, "REED_API_KEY"),
        sync_secret=_optional(source, "SYNC_SECRET"),
        data_dir=Path(data_dir_raw).expanduser(),
        database_url=database_url_raw,
        database_url_explicit=database_url_explicit,
        vacancy_cache_ttl=_int(source, "VACANCY_CACHE_TTL", 1800, minimum=1),
        vacancy_page_size=_int(source, "VACANCY_PAGE_SIZE", 60, minimum=1, maximum=100),
        search_page_size=_int(source, "SEARCH_PAGE_SIZE", 20, minimum=1, maximum=60),
        search_snapshot_ttl_seconds=_int(
            source,
            "SEARCH_SNAPSHOT_TTL_SECONDS",
            1800,
            minimum=300,
            maximum=86_400,
        ),
        search_snapshot_max_candidates=_int(
            source,
            "SEARCH_SNAPSHOT_MAX_CANDIDATES",
            1200,
            minimum=60,
            maximum=10_000,
        ),
        search_snapshot_max_pages_per_source=_int(
            source,
            "SEARCH_SNAPSHOT_MAX_PAGES_PER_SOURCE",
            8,
            minimum=1,
            maximum=100,
        ),
        search_snapshot_max_rounds_per_request=_int(
            source,
            "SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST",
            1,
            minimum=1,
            maximum=20,
        ),
        search_snapshot_buffer_items=_int(
            source,
            "SEARCH_SNAPSHOT_BUFFER_ITEMS",
            1,
            minimum=1,
            maximum=100,
        ),
        search_snapshot_extension_lease_seconds=_int(
            source,
            "SEARCH_SNAPSHOT_EXTENSION_LEASE_SECONDS",
            90,
            minimum=15,
            maximum=600,
        ),
        trudvsem_sync_interval=_int(source, "TRUDVSEM_SYNC_INTERVAL", 1800, minimum=1),
        trudvsem_sync_items=_int(source, "TRUDVSEM_SYNC_ITEMS", 300, minimum=1, maximum=500),
        trudvsem_sync_batch=_int(source, "TRUDVSEM_SYNC_BATCH", 10, minimum=1, maximum=10),
        trudvsem_request_attempts=_int(
            source,
            "TRUDVSEM_REQUEST_ATTEMPTS",
            5,
            minimum=1,
            maximum=10,
        ),
        trudvsem_retry_backoff=_float(
            source,
            "TRUDVSEM_RETRY_BACKOFF",
            1.0,
            minimum=0.0,
            maximum=60.0,
        ),
        trudvsem_sync_enabled=_bool(
            source,
            "TRUDVSEM_SYNC_ENABLED",
            sync_enabled_default,
        ),
        trudvsem_sync_poll_seconds=_int(
            source,
            "TRUDVSEM_SYNC_POLL_SECONDS",
            15,
            minimum=2,
            maximum=300,
        ),
        trudvsem_sync_stale_seconds=_int(
            source,
            "TRUDVSEM_SYNC_STALE_SECONDS",
            900,
            minimum=120,
            maximum=86400,
        ),
        trudvsem_worker_heartbeat_seconds=_int(
            source,
            "TRUDVSEM_WORKER_HEARTBEAT_SECONDS",
            15,
            minimum=2,
            maximum=300,
        ),
        trudvsem_sync_watermark_overlap_seconds=_int(
            source,
            "TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS",
            300,
            minimum=0,
            maximum=86_400,
        ),
        trudvsem_vacancy_ttl_days=_int(
            source,
            "TRUDVSEM_VACANCY_TTL_DAYS",
            45,
            minimum=31,
            maximum=365,
        ),
        trudvsem_closed_retention_days=_int(
            source,
            "TRUDVSEM_CLOSED_RETENTION_DAYS",
            30,
            minimum=1,
            maximum=365,
        ),
        trudvsem_retry_base_seconds=trudvsem_retry_base_seconds,
        trudvsem_retry_max_seconds=trudvsem_retry_max_seconds,
        debug_hh=_bool(source, "DEBUG_HH", False),
        hh_currency_scan_pages=_int(
            source,
            "HH_CURRENCY_SCAN_PAGES",
            20,
            minimum=1,
            maximum=20,
        ),
        max_resume_upload_mb=_int(
            source,
            "MAX_RESUME_UPLOAD_MB",
            8,
            minimum=1,
            maximum=25,
        ),
        max_resume_pages=_int(
            source,
            "MAX_RESUME_PAGES",
            30,
            minimum=1,
            maximum=100,
        ),
        max_resume_text_characters=_int(
            source,
            "MAX_RESUME_TEXT_CHARACTERS",
            200_000,
            minimum=10_000,
            maximum=2_000_000,
        ),
        session_cookie_secure=session_cookie_secure,
        session_cookie_samesite=session_cookie_samesite,
        session_lifetime_seconds=_int(
            source,
            "SESSION_LIFETIME_SECONDS",
            43_200,
            minimum=900,
            maximum=604_800,
        ),
        auth_session_ttl_seconds=_int(
            source,
            "AUTH_SESSION_TTL_SECONDS",
            43_200,
            minimum=900,
            maximum=2_592_000,
        ),
        auth_verification_ttl_seconds=_int(
            source,
            "AUTH_VERIFICATION_TTL_SECONDS",
            86_400,
            minimum=900,
            maximum=604_800,
        ),
        auth_reset_ttl_seconds=_int(
            source,
            "AUTH_RESET_TTL_SECONDS",
            3_600,
            minimum=300,
            maximum=86_400,
        ),
        auth_password_min_length=_int(
            source,
            "AUTH_PASSWORD_MIN_LENGTH",
            12,
            minimum=10,
            maximum=64,
        ),
        auth_email_backend=auth_email_backend,
        auth_email_from=auth_email_from,
        auth_email_from_name=_clean(source.get("AUTH_EMAIL_FROM_NAME", "AI Career Agent")) or "AI Career Agent",
        auth_smtp_host=auth_smtp_host,
        auth_smtp_port=_int(source, "AUTH_SMTP_PORT", 587, minimum=1, maximum=65535),
        auth_smtp_username=auth_smtp_username,
        auth_smtp_password=auth_smtp_password,
        auth_smtp_use_tls=auth_smtp_use_tls,
        auth_smtp_use_ssl=auth_smtp_use_ssl,
        auth_smtp_timeout_seconds=_float(
            source,
            "AUTH_SMTP_TIMEOUT_SECONDS",
            8.0,
            minimum=1.0,
            maximum=30.0,
        ),
        csrf_enabled=csrf_enabled,
        csrf_time_limit_seconds=_int(
            source,
            "CSRF_TIME_LIMIT_SECONDS",
            7_200,
            minimum=300,
            maximum=86_400,
        ),
        rate_limit_enabled=rate_limit_enabled,
        rate_limit_storage_uri=_clean(
            source.get("RATELIMIT_STORAGE_URI", "memory://")
        )
        or "memory://",
        trusted_hosts=trusted_hosts,
        trust_proxy_headers=_bool(
            source,
            "TRUST_PROXY_HEADERS",
            environment == "production",
        ),
        security_headers_enabled=security_headers_enabled,
        hsts_seconds=_int(
            source,
            "HSTS_SECONDS",
            31_536_000,
            minimum=0,
            maximum=63_072_000,
        ),
        max_form_memory_size=_int(
            source,
            "MAX_FORM_MEMORY_SIZE",
            262_144,
            minimum=16_384,
            maximum=2_097_152,
        ),
        max_form_parts=_int(
            source,
            "MAX_FORM_PARTS",
            32,
            minimum=4,
            maximum=256,
        ),
        debug_diagnostics=debug_diagnostics,
        diagnostics_secret=diagnostics_secret,
        service_name=_service_name(source),
        app_version=_app_version(source),
        log_level=_choice(
            {**source, "LOG_LEVEL": _clean(source.get("LOG_LEVEL", "INFO")).upper()},
            "LOG_LEVEL",
            "INFO",
            choices={"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"},
        ),
        log_format=_choice(
            {**source, "LOG_FORMAT": _clean(source.get("LOG_FORMAT", "json" if environment == "production" else "text")).lower()},
            "LOG_FORMAT",
            "json" if environment == "production" else "text",
            choices={"json", "text"},
        ),
        ops_alert_webhook_url=ops_alert_webhook_url,
        ops_alert_webhook_token=_optional(source, "OPS_ALERT_WEBHOOK_TOKEN"),
        ops_alert_timeout_seconds=_float(
            source,
            "OPS_ALERT_TIMEOUT_SECONDS",
            3.0,
            minimum=0.5,
            maximum=15.0,
        ),
        ops_alert_min_level=_choice(
            {**source, "OPS_ALERT_MIN_LEVEL": _clean(source.get("OPS_ALERT_MIN_LEVEL", "ERROR")).upper()},
            "OPS_ALERT_MIN_LEVEL",
            "ERROR",
            choices={"WARNING", "ERROR", "CRITICAL"},
        ),
        render_region=_clean(source.get("RENDER_REGION", "unknown")) or "unknown",
        port=_int(source, "PORT", 10000, minimum=1, maximum=65535),
        flask_debug=_bool(source, "FLASK_DEBUG", flask_debug_default),
    )
