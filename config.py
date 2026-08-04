"""Central application configuration for development, test, and production.

The module reads environment variables in one place and returns an immutable
``AppSettings`` object. Production and development never receive built-in
secrets. Deterministic placeholder credentials exist only for the test mode so
that the test suite can import the Flask application without real API keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

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
}


def _clean(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def _optional(source: Mapping[str, str], name: str, default: str = "") -> str | None:
    value = _clean(source.get(name, default))
    return value or None


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
    vacancy_cache_ttl: int
    vacancy_page_size: int
    trudvsem_sync_interval: int
    trudvsem_sync_items: int
    trudvsem_sync_batch: int
    trudvsem_request_attempts: int
    trudvsem_retry_backoff: float
    trudvsem_sync_enabled: bool
    debug_hh: bool
    hh_currency_scan_pages: int
    max_resume_upload_mb: int
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

    return AppSettings(
        environment=environment,
        flask_secret_key=_required(source, "FLASK_SECRET_KEY"),
        token_encryption_key=token_encryption_key,
        superjob_client_id=_required(source, "SUPERJOB_CLIENT_ID"),
        superjob_client_secret=_required(source, "SUPERJOB_CLIENT_SECRET"),
        superjob_redirect_uri=_required(source, "SUPERJOB_REDIRECT_URI"),
        hh_client_id=_required(source, "HH_CLIENT_ID"),
        hh_client_secret=_required(source, "HH_CLIENT_SECRET"),
        hh_redirect_uri=_required(source, "HH_REDIRECT_URI"),
        hh_user_agent=_required(source, "HH_USER_AGENT"),
        hh_app_token=_optional(source, "HH_APP_TOKEN"),
        reed_api_key=_optional(source, "REED_API_KEY"),
        sync_secret=_optional(source, "SYNC_SECRET"),
        data_dir=Path(data_dir_raw).expanduser(),
        vacancy_cache_ttl=_int(source, "VACANCY_CACHE_TTL", 1800, minimum=1),
        vacancy_page_size=_int(source, "VACANCY_PAGE_SIZE", 60, minimum=1, maximum=100),
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
        render_region=_clean(source.get("RENDER_REGION", "unknown")) or "unknown",
        port=_int(source, "PORT", 10000, minimum=1, maximum=65535),
        flask_debug=_bool(source, "FLASK_DEBUG", flask_debug_default),
    )
