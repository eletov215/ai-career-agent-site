from __future__ import annotations

from types import SimpleNamespace

from config import load_settings
from services.admin_access import is_search_admin


def test_admin_allowlist_requires_active_verified_exact_email():
    settings = load_settings({"APP_ENV": "test", "SEARCH_ADMIN_EMAILS": "Owner@Example.test"})
    base = SimpleNamespace(
        status="active",
        email_verified_at=123,
        normalized_email="owner@example.test",
        email="owner@example.test",
    )
    assert is_search_admin(base, settings) is True
    assert is_search_admin(SimpleNamespace(**{**base.__dict__, "normalized_email": "other@example.test", "email": "other@example.test"}), settings) is False
    assert is_search_admin(SimpleNamespace(**{**base.__dict__, "status": "pending"}), settings) is False
    assert is_search_admin(SimpleNamespace(**{**base.__dict__, "email_verified_at": None}), settings) is False


def test_empty_allowlist_disables_admin_access():
    settings = load_settings({"APP_ENV": "test", "SEARCH_ADMIN_EMAILS": ""})
    user = SimpleNamespace(status="active", email_verified_at=123, normalized_email="owner@example.test", email="owner@example.test")
    assert is_search_admin(user, settings) is False
