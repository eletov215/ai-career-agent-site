"""Explicit SEARCH-005 administrator authorization boundary."""

from __future__ import annotations

from typing import Any


def normalize_admin_email(value: str | None) -> str:
    return str(value or "").strip().casefold()


def is_search_admin(user: Any, settings: Any) -> bool:
    """Return True only for active, verified, explicitly allowlisted users."""

    if user is None:
        return False
    if str(getattr(user, "status", "")) != "active":
        return False
    if getattr(user, "email_verified_at", None) is None:
        return False
    normalized = normalize_admin_email(getattr(user, "normalized_email", None) or getattr(user, "email", None))
    if not normalized:
        return False
    allowed = {
        normalize_admin_email(item)
        for item in getattr(settings, "search_admin_emails", ())
        if normalize_admin_email(item)
    }
    return normalized in allowed
