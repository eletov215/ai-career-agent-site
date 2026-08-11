from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from config import ConfigurationError, load_database_url, load_settings


VALID_FERNET_KEY = "yPWPkxw3j4ZWDVBQ-i3kryGBFjd-5Bjg2tDjCNUMciw="


def production_environment(**overrides: str) -> dict[str, str]:
    values = {
        "APP_ENV": "production",
        "FLASK_SECRET_KEY": "production-secret",
        "TOKEN_ENCRYPTION_KEY": VALID_FERNET_KEY,
        "SUPERJOB_CLIENT_ID": "sj-id",
        "SUPERJOB_CLIENT_SECRET": "sj-secret",
        "SUPERJOB_REDIRECT_URI": "https://example.test/oauth/superjob/callback",
        "HH_CLIENT_ID": "hh-id",
        "HH_CLIENT_SECRET": "hh-secret",
        "HH_REDIRECT_URI": "https://example.test/oauth/hh/callback",
        "HH_USER_AGENT": "AI-Career-Agent-Test/1.0 (owner@example.test)",
    }
    values.update(overrides)
    return values


def test_test_environment_requires_no_real_secrets():
    settings = load_settings({"APP_ENV": "test"})

    assert settings.environment == "test"
    assert settings.is_test is True
    assert settings.flask_secret_key == "test-only-flask-secret"
    assert settings.superjob_client_id == "test-superjob-client"
    assert settings.hh_user_agent.endswith("tests@example.invalid)")
    assert settings.trudvsem_sync_enabled is False
    assert settings.flask_mapping()["TESTING"] is True
    assert settings.diagnostics_secret == "test-diagnostics-secret"
    assert settings.session_cookie_secure is False
    assert settings.csrf_enabled is True
    assert settings.rate_limit_enabled is True
    assert settings.auth_email_backend == "memory"
    assert settings.auth_session_ttl_seconds == 43_200


def test_production_reports_all_missing_required_variables():
    with pytest.raises(ConfigurationError) as error:
        load_settings({"APP_ENV": "production"})

    message = str(error.value)
    assert "Ошибка конфигурации (production)" in message
    assert "FLASK_SECRET_KEY" in message
    assert "TOKEN_ENCRYPTION_KEY" in message
    assert "HH_USER_AGENT" in message
    assert "Render -> Environment" in message


def test_development_requires_explicit_secrets_and_enables_debug_by_default():
    environment = production_environment(APP_ENV="development")
    settings = load_settings(environment)

    assert settings.environment == "development"
    assert settings.is_development is True
    assert settings.flask_debug is True
    assert settings.trudvsem_sync_enabled is True


def test_missing_app_env_defaults_to_production_for_existing_render_service():
    environment = production_environment()
    environment.pop("APP_ENV")

    settings = load_settings(environment)

    assert settings.is_production is True


def test_production_defaults_preserve_current_runtime_behavior():
    settings = load_settings(production_environment())

    assert settings.is_production is True
    assert settings.data_dir == Path("/tmp/ai-career-agent")
    assert settings.database_url.startswith("sqlite:////tmp/ai-career-agent/app.db")
    assert settings.database_url_explicit is False
    assert settings.vacancy_cache_ttl == 1800
    assert settings.vacancy_page_size == 60
    assert settings.search_page_size == 20
    assert settings.search_snapshot_ttl_seconds == 1800
    assert settings.search_snapshot_max_candidates == 1200
    assert settings.search_snapshot_max_pages_per_source == 8
    assert settings.search_snapshot_max_rounds_per_request == 1
    assert settings.search_snapshot_buffer_items == 1
    assert settings.search_snapshot_extension_lease_seconds == 90
    assert settings.trudvsem_sync_items == 300
    assert settings.trudvsem_sync_batch == 10
    assert settings.trudvsem_sync_poll_seconds == 15
    assert settings.trudvsem_sync_stale_seconds == 900
    assert settings.trudvsem_worker_heartbeat_seconds == 15
    assert settings.max_resume_upload_mb == 8
    assert settings.max_resume_pages == 30
    assert settings.max_resume_text_characters == 200_000
    assert settings.hh_currency_scan_pages == 20
    assert settings.session_cookie_secure is True
    assert settings.session_cookie_samesite == "Lax"
    assert settings.auth_email_backend == "disabled"
    assert settings.auth_session_ttl_seconds == 43_200
    assert settings.auth_verification_ttl_seconds == 86_400
    assert settings.auth_reset_ttl_seconds == 3_600
    assert settings.auth_password_min_length == 12
    assert settings.csrf_enabled is True
    assert settings.rate_limit_enabled is True
    assert settings.security_headers_enabled is True
    assert settings.rate_limit_storage_uri == "memory://"
    assert settings.service_name == "ai-career-agent"
    assert settings.app_version == "development"
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"
    assert settings.ops_alert_webhook_url is None
    assert settings.ops_alert_min_level == "ERROR"
    assert settings.ops_alert_timeout_seconds == 3.0
    assert "example.test" in settings.trusted_hosts
    mapping = settings.flask_mapping()
    assert mapping["SESSION_COOKIE_HTTPONLY"] is True
    assert mapping["SESSION_COOKIE_SECURE"] is True
    assert mapping["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert mapping["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=12)
    assert mapping["WTF_CSRF_TIME_LIMIT"] == 7200
    assert isinstance(mapping["WTF_CSRF_TIME_LIMIT"], int)
    assert mapping["TRUST_PROXY_HEADERS"] is True
    assert mapping["MAX_CONTENT_LENGTH"] == 9 * 1024 * 1024
    assert settings.port == 10000
    assert settings.flask_debug is False


def test_numeric_and_boolean_values_are_validated_centrally(tmp_path):
    settings = load_settings(
        production_environment(
            DATA_DIR=str(tmp_path),
            VACANCY_PAGE_SIZE="40",
            SEARCH_PAGE_SIZE="24",
            SEARCH_SNAPSHOT_TTL_SECONDS="2400",
            SEARCH_SNAPSHOT_MAX_CANDIDATES="1600",
            SEARCH_SNAPSHOT_MAX_PAGES_PER_SOURCE="12",
            SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST="4",
            SEARCH_SNAPSHOT_BUFFER_ITEMS="6",
            SEARCH_SNAPSHOT_EXTENSION_LEASE_SECONDS="120",
            TRUDVSEM_SYNC_ENABLED="no",
            TRUDVSEM_SYNC_POLL_SECONDS="20",
            TRUDVSEM_SYNC_STALE_SECONDS="900",
            TRUDVSEM_WORKER_HEARTBEAT_SECONDS="12",
            TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS="420",
            TRUDVSEM_VACANCY_TTL_DAYS="60",
            TRUDVSEM_CLOSED_RETENTION_DAYS="21",
            TRUDVSEM_RETRY_BASE_SECONDS="30",
            TRUDVSEM_RETRY_MAX_SECONDS="900",
            TRUDVSEM_RETRY_BACKOFF="0.25",
            HH_CURRENCY_SCAN_PAGES="7",
            MAX_RESUME_UPLOAD_MB="12",
            MAX_RESUME_PAGES="45",
            MAX_RESUME_TEXT_CHARACTERS="300000",
            SESSION_LIFETIME_SECONDS="3600",
            AUTH_SESSION_TTL_SECONDS="7200",
            AUTH_VERIFICATION_TTL_SECONDS="172800",
            AUTH_RESET_TTL_SECONDS="1800",
            AUTH_PASSWORD_MIN_LENGTH="14",
            AUTH_EMAIL_BACKEND="smtp",
            AUTH_EMAIL_FROM="accounts@example.test",
            AUTH_SMTP_HOST="smtp.example.test",
            AUTH_SMTP_PORT="2525",
            AUTH_SMTP_USERNAME="mailer",
            AUTH_SMTP_PASSWORD="mail-secret",
            AUTH_SMTP_USE_TLS="yes",
            AUTH_SMTP_USE_SSL="no",
            AUTH_SMTP_TIMEOUT_SECONDS="6.5",
            CSRF_TIME_LIMIT_SECONDS="1800",
            MAX_FORM_MEMORY_SIZE="131072",
            MAX_FORM_PARTS="20",
            SERVICE_NAME="career-service",
            APP_VERSION="test-version",
            LOG_LEVEL="warning",
            LOG_FORMAT="text",
            OPS_ALERT_WEBHOOK_URL="https://alerts.example.test/hooks/ops",
            OPS_ALERT_TIMEOUT_SECONDS="4.5",
            OPS_ALERT_MIN_LEVEL="critical",
            PORT="11000",
        )
    )

    assert settings.data_dir == tmp_path
    assert settings.vacancy_page_size == 40
    assert settings.search_page_size == 24
    assert settings.search_snapshot_ttl_seconds == 2400
    assert settings.search_snapshot_max_candidates == 1600
    assert settings.search_snapshot_max_pages_per_source == 12
    assert settings.search_snapshot_max_rounds_per_request == 4
    assert settings.search_snapshot_buffer_items == 6
    assert settings.search_snapshot_extension_lease_seconds == 120
    assert settings.trudvsem_sync_enabled is False
    assert settings.trudvsem_sync_poll_seconds == 20
    assert settings.trudvsem_sync_stale_seconds == 900
    assert settings.trudvsem_worker_heartbeat_seconds == 12
    assert settings.trudvsem_sync_watermark_overlap_seconds == 420
    assert settings.trudvsem_vacancy_ttl_days == 60
    assert settings.trudvsem_closed_retention_days == 21
    assert settings.trudvsem_retry_base_seconds == 30
    assert settings.trudvsem_retry_max_seconds == 900
    assert settings.trudvsem_retry_backoff == 0.25
    assert settings.hh_currency_scan_pages == 7
    assert settings.max_resume_upload_mb == 12
    assert settings.max_resume_pages == 45
    assert settings.max_resume_text_characters == 300_000
    assert settings.session_lifetime_seconds == 3600
    assert settings.auth_session_ttl_seconds == 7200
    assert settings.auth_verification_ttl_seconds == 172800
    assert settings.auth_reset_ttl_seconds == 1800
    assert settings.auth_password_min_length == 14
    assert settings.auth_email_backend == "smtp"
    assert settings.auth_email_from == "accounts@example.test"
    assert settings.auth_smtp_host == "smtp.example.test"
    assert settings.auth_smtp_port == 2525
    assert settings.auth_smtp_use_tls is True
    assert settings.auth_smtp_use_ssl is False
    assert settings.auth_smtp_timeout_seconds == 6.5
    assert settings.csrf_time_limit_seconds == 1800
    assert settings.max_form_memory_size == 131_072
    assert settings.max_form_parts == 20
    assert settings.service_name == "career-service"
    assert settings.app_version == "test-version"
    assert settings.log_level == "WARNING"
    assert settings.log_format == "text"
    assert settings.ops_alert_webhook_url == "https://alerts.example.test/hooks/ops"
    assert settings.ops_alert_timeout_seconds == 4.5
    assert settings.ops_alert_min_level == "CRITICAL"
    assert settings.port == 11000


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("TRUDVSEM_SYNC_ENABLED", "sometimes", "true/false"),
        ("TRUDVSEM_SYNC_POLL_SECONDS", "1", "не может быть меньше 2"),
        ("TRUDVSEM_SYNC_STALE_SECONDS", "60", "не может быть меньше 120"),
        ("TRUDVSEM_WORKER_HEARTBEAT_SECONDS", "301", "не может быть больше 300"),
        (
            "TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS",
            "86401",
            "не может быть больше 86400",
        ),
        ("TRUDVSEM_VACANCY_TTL_DAYS", "30", "не может быть меньше 31"),
        (
            "TRUDVSEM_CLOSED_RETENTION_DAYS",
            "0",
            "не может быть меньше 1",
        ),
        ("TRUDVSEM_RETRY_BASE_SECONDS", "4", "не может быть меньше 5"),
        ("TRUDVSEM_RETRY_MAX_SECONDS", "29", "не может быть меньше 30"),
        ("VACANCY_PAGE_SIZE", "many", "целое число"),
        ("SEARCH_PAGE_SIZE", "61", "не может быть больше 60"),
        ("SEARCH_SNAPSHOT_TTL_SECONDS", "299", "не может быть меньше 300"),
        ("SEARCH_SNAPSHOT_MAX_CANDIDATES", "59", "не может быть меньше 60"),
        ("SEARCH_SNAPSHOT_MAX_PAGES_PER_SOURCE", "101", "не может быть больше 100"),
        ("SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST", "21", "не может быть больше 20"),
        ("SEARCH_SNAPSHOT_BUFFER_ITEMS", "0", "не может быть меньше 1"),
        ("SEARCH_SNAPSHOT_EXTENSION_LEASE_SECONDS", "14", "не может быть меньше 15"),
        ("MAX_RESUME_UPLOAD_MB", "26", "не может быть больше 25"),
        ("MAX_RESUME_PAGES", "101", "не может быть больше 100"),
        ("SESSION_COOKIE_SAMESITE", "None", "Разрешены"),
        ("SESSION_LIFETIME_SECONDS", "60", "не может быть меньше 900"),
        ("AUTH_SESSION_TTL_SECONDS", "60", "не может быть меньше 900"),
        ("AUTH_VERIFICATION_TTL_SECONDS", "60", "не может быть меньше 900"),
        ("AUTH_RESET_TTL_SECONDS", "60", "не может быть меньше 300"),
        ("AUTH_PASSWORD_MIN_LENGTH", "9", "не может быть меньше 10"),
        ("AUTH_EMAIL_BACKEND", "provider", "Разрешены"),
        ("AUTH_SMTP_TIMEOUT_SECONDS", "0.5", "не может быть меньше 1.0"),
        ("LOG_LEVEL", "verbose", "Разрешены"),
        ("LOG_FORMAT", "xml", "Разрешены"),
        ("SERVICE_NAME", "bad service", "SERVICE_NAME"),
        ("OPS_ALERT_TIMEOUT_SECONDS", "0.1", "не может быть меньше 0.5"),
        ("PORT", "0", "не может быть меньше 1"),
    ],
)
def test_invalid_runtime_values_have_clear_errors(name, value, expected):
    environment = production_environment(**{name: value})

    with pytest.raises(ConfigurationError, match=expected):
        load_settings(environment)


def test_trudvsem_retry_ceiling_cannot_be_below_base():
    with pytest.raises(ConfigurationError, match="RETRY_MAX_SECONDS"):
        load_settings(
            production_environment(
                TRUDVSEM_RETRY_BASE_SECONDS="300",
                TRUDVSEM_RETRY_MAX_SECONDS="120",
            )
        )


def test_invalid_environment_name_is_rejected():
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        load_settings({"APP_ENV": "staging"})


def test_invalid_fernet_key_is_rejected_without_exposing_secret():
    with pytest.raises(ConfigurationError) as error:
        load_settings(production_environment(TOKEN_ENCRYPTION_KEY="not-a-fernet-key"))

    assert "TOKEN_ENCRYPTION_KEY" in str(error.value)
    assert "not-a-fernet-key" not in str(error.value)


def test_render_postgres_url_is_normalized_to_psycopg3():
    settings = load_settings(
        production_environment(
            DATABASE_URL="postgresql://user:password@db.example.test/career"
        )
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.database_url_explicit is True


def test_database_url_loader_does_not_require_oauth_secrets(tmp_path):
    database_url, explicit = load_database_url(
        {"APP_ENV": "development", "DATA_DIR": str(tmp_path)}
    )

    assert database_url == f"sqlite:///{(tmp_path / 'app.db').resolve().as_posix()}"
    assert explicit is False


def test_unsupported_database_driver_is_rejected_without_echoing_credentials():
    environment = production_environment(
        DATABASE_URL="mysql://secret-user:secret-password@example.test/career"
    )
    with pytest.raises(ConfigurationError) as error:
        load_settings(environment)

    assert "DATABASE_URL" in str(error.value)
    assert "secret-password" not in str(error.value)


@pytest.mark.parametrize(
    "setting",
    [
        "SESSION_COOKIE_SECURE",
        "CSRF_ENABLED",
        "RATE_LIMIT_ENABLED",
        "SECURITY_HEADERS_ENABLED",
    ],
)
def test_production_rejects_disabled_security_controls(setting):
    with pytest.raises(ConfigurationError, match=setting):
        load_settings(production_environment(**{setting: "0"}))


def test_production_requires_lax_same_site_for_oauth_callbacks():
    with pytest.raises(ConfigurationError, match="SESSION_COOKIE_SAMESITE=Lax"):
        load_settings(
            production_environment(SESSION_COOKIE_SAMESITE="Strict")
        )


def test_diagnostics_require_a_separate_secret_when_enabled():
    with pytest.raises(ConfigurationError, match="DIAGNOSTICS_SECRET"):
        load_settings(
            production_environment(
                DEBUG_DIAGNOSTICS="1",
                DIAGNOSTICS_SECRET="",
            )
        )


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        (
            "HH_REDIRECT_URI",
            "http://example.test/oauth/hh/callback",
            "production должен использовать HTTPS",
        ),
        (
            "SUPERJOB_REDIRECT_URI",
            "https://user:password@example.test/oauth/superjob/callback",
            "без credentials",
        ),
        (
            "HH_REDIRECT_URI",
            "https://example.test/oauth/hh/callback#token",
            "без credentials и fragment",
        ),
    ],
)
def test_production_rejects_insecure_oauth_redirect_uris(name, value, expected):
    with pytest.raises(ConfigurationError, match=expected):
        load_settings(production_environment(**{name: value}))


def test_explicit_trusted_hosts_are_combined_with_oauth_hosts():
    settings = load_settings(
        production_environment(
            TRUSTED_HOSTS="ai-career.example,app.ai-career.example"
        )
    )

    assert settings.trusted_hosts == (
        "ai-career.example",
        "app.ai-career.example",
        "example.test",
    )


def test_production_alert_webhook_requires_https():
    with pytest.raises(ConfigurationError, match="OPS_ALERT_WEBHOOK_URL.*HTTPS"):
        load_settings(
            production_environment(
                OPS_ALERT_WEBHOOK_URL="http://alerts.example.test/hook",
            )
        )


def test_alert_webhook_rejects_embedded_credentials():
    with pytest.raises(ConfigurationError, match="credentials"):
        load_settings(
            production_environment(
                OPS_ALERT_WEBHOOK_URL="https://user:secret@alerts.example.test/hook",
            )
        )


def test_smtp_backend_requires_host_and_sender():
    with pytest.raises(ConfigurationError, match="AUTH_EMAIL_BACKEND=smtp"):
        load_settings(production_environment(AUTH_EMAIL_BACKEND="smtp"))


def test_production_rejects_memory_auth_email_backend():
    with pytest.raises(ConfigurationError, match="memory запрещён"):
        load_settings(production_environment(AUTH_EMAIL_BACKEND="memory"))


def test_production_smtp_requires_encrypted_transport():
    with pytest.raises(ConfigurationError, match="защищённый режим"):
        load_settings(
            production_environment(
                AUTH_EMAIL_BACKEND="smtp",
                AUTH_EMAIL_FROM="accounts@example.test",
                AUTH_SMTP_HOST="smtp.example.test",
                AUTH_SMTP_USE_TLS="no",
                AUTH_SMTP_USE_SSL="no",
            )
        )


def test_production_smtp_accepts_implicit_ssl():
    settings = load_settings(
        production_environment(
            AUTH_EMAIL_BACKEND="smtp",
            AUTH_EMAIL_FROM="accounts@example.test",
            AUTH_SMTP_HOST="smtp.example.test",
            AUTH_SMTP_PORT="465",
            AUTH_SMTP_USE_TLS="no",
            AUTH_SMTP_USE_SSL="yes",
        )
    )
    assert settings.auth_smtp_use_tls is False
    assert settings.auth_smtp_use_ssl is True
    assert settings.auth_smtp_port == 465


def test_smtp_rejects_starttls_and_implicit_ssl_together():
    with pytest.raises(ConfigurationError, match="нельзя включать одновременно"):
        load_settings(
            production_environment(
                AUTH_EMAIL_BACKEND="smtp",
                AUTH_EMAIL_FROM="accounts@example.test",
                AUTH_SMTP_HOST="smtp.example.test",
                AUTH_SMTP_USE_TLS="yes",
                AUTH_SMTP_USE_SSL="yes",
            )
        )


def test_development_smtp_can_disable_tls_for_local_mail_sink():
    settings = load_settings(
        production_environment(
            APP_ENV="development",
            AUTH_EMAIL_BACKEND="smtp",
            AUTH_EMAIL_FROM="accounts@example.test",
            AUTH_SMTP_HOST="localhost",
            AUTH_SMTP_USE_TLS="no",
        )
    )
    assert settings.auth_smtp_use_tls is False
