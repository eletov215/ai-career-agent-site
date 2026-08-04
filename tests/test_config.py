from __future__ import annotations

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
    assert settings.trudvsem_sync_items == 300
    assert settings.trudvsem_sync_batch == 10
    assert settings.max_resume_upload_mb == 8
    assert settings.hh_currency_scan_pages == 20
    assert settings.port == 10000
    assert settings.flask_debug is False


def test_numeric_and_boolean_values_are_validated_centrally(tmp_path):
    settings = load_settings(
        production_environment(
            DATA_DIR=str(tmp_path),
            VACANCY_PAGE_SIZE="40",
            TRUDVSEM_SYNC_ENABLED="no",
            TRUDVSEM_RETRY_BACKOFF="0.25",
            HH_CURRENCY_SCAN_PAGES="7",
            MAX_RESUME_UPLOAD_MB="12",
            PORT="11000",
        )
    )

    assert settings.data_dir == tmp_path
    assert settings.vacancy_page_size == 40
    assert settings.trudvsem_sync_enabled is False
    assert settings.trudvsem_retry_backoff == 0.25
    assert settings.hh_currency_scan_pages == 7
    assert settings.max_resume_upload_mb == 12
    assert settings.port == 11000


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("TRUDVSEM_SYNC_ENABLED", "sometimes", "true/false"),
        ("VACANCY_PAGE_SIZE", "many", "целое число"),
        ("MAX_RESUME_UPLOAD_MB", "26", "не может быть больше 25"),
        ("PORT", "0", "не может быть меньше 1"),
    ],
)
def test_invalid_runtime_values_have_clear_errors(name, value, expected):
    environment = production_environment(**{name: value})

    with pytest.raises(ConfigurationError, match=expected):
        load_settings(environment)


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
