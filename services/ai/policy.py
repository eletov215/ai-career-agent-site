"""Mutable technical policy; monetary units are integer micro-RUB (not floats).

The dated rate snapshot is an internal estimate, never a payment authorization.
BILL-001 will set plan entitlements separately. No commercial quotas are seeded.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
import copy

DEFAULT_POLICY = {
    "enabled": False, "kill_switch": True, "commercial_enforcement_enabled": False,
    "max_input_tokens": 8000, "max_output_tokens": 1600, "max_attempts": 2,
    "max_global_concurrency": 2, "max_user_concurrency": 1,
    "user_daily_requests": 100, "global_daily_requests": 1000,
    "user_daily_budget_microrub": 200_000_000, "global_daily_budget_microrub": 1_000_000_000,
    "global_monthly_budget_microrub": 20_000_000_000,
    "input_microrub_per_token": 500, "output_microrub_per_token": 1200,
    "pricing_checked_on": "2026-09-14", "pricing_valid_days": 30,
    "attempt_timeout_seconds": 25, "total_timeout_seconds": 55, "retry_delay_seconds": 1,
    "lease_seconds": 90, "circuit_failures": 3, "circuit_cooldown_seconds": 60,
    "metadata_retention_days": 30,
}

RANGES = {
    "max_input_tokens": (1,8000), "max_output_tokens": (1,1600), "max_attempts": (1,2),
    "max_global_concurrency": (1,20), "max_user_concurrency": (1,5),
    "user_daily_requests": (1,10000), "global_daily_requests": (1,100000),
    "user_daily_budget_microrub": (1,1_000_000_000_000),
    "global_daily_budget_microrub": (1,1_000_000_000_000),
    "global_monthly_budget_microrub": (1,10_000_000_000_000),
    "input_microrub_per_token": (1,1000000), "output_microrub_per_token": (1,1000000),
    "pricing_valid_days": (1,30), "attempt_timeout_seconds": (1,25),
    "total_timeout_seconds": (1,55), "retry_delay_seconds": (0,2), "lease_seconds": (60,180),
    "circuit_failures": (1,10), "circuit_cooldown_seconds": (60,3600),
    "metadata_retention_days": (1,30),
}

def validate_policy(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != set(DEFAULT_POLICY):
        raise ValueError("AI policy fields are missing or unknown")
    for key, (low, high) in RANGES.items():
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError(f"Invalid technical control: {key}")
    for key in ("enabled", "kill_switch", "commercial_enforcement_enabled"):
        if type(value[key]) is not bool:
            raise ValueError(f"Invalid boolean control: {key}")
    try:
        if date.fromisoformat(value["pricing_checked_on"]).isoformat() != value["pricing_checked_on"]:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Invalid pricing date") from None
    if not (value["user_daily_budget_microrub"] <= value["global_daily_budget_microrub"] <= value["global_monthly_budget_microrub"]):
        raise ValueError("Budget order must be user <= global daily <= global monthly")
    if value["user_daily_requests"] > value["global_daily_requests"] or value["max_user_concurrency"] > value["max_global_concurrency"]:
        raise ValueError("User controls must not exceed global controls")
    if value["lease_seconds"] <= value["total_timeout_seconds"] + 10:
        raise ValueError("Lease must exceed the hard provider deadline with settlement margin")
    return copy.deepcopy(value)

def cost_microrub(input_tokens: int, output_tokens: int, policy: dict) -> int:
    if any(type(n) is not int or not 0 <= n <= 1_000_000 for n in (input_tokens,output_tokens)):
        raise ValueError("Invalid token counters")
    return input_tokens*policy["input_microrub_per_token"] + output_tokens*policy["output_microrub_per_token"]

def rub_to_micro(value: str) -> int:
    from decimal import InvalidOperation
    import re
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,6})?", value or ""):
        raise ValueError("Expected positive RUB decimal, at most six fraction digits")
    try:
        v=Decimal(value)*1_000_000
        if not v.is_finite() or not 0 < v <= 10_000_000_000_000:
            raise ValueError
        return int(v)
    except (InvalidOperation,ValueError):
        raise ValueError("RUB amount out of range") from None
