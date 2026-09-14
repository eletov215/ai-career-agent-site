#!/usr/bin/env python3
"""AI-PROVIDER-001 offline policy validation and Decimal cost planning.

This module performs no network I/O, reads no secrets/environment, and is NOT a
runtime AI adapter, rate limiter, consent guard, or financial ledger. Production
activation belongs to AI-001 after LEGAL-001 and the other documented gates.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs/policies/ai_provider_policy.v1.json"
BENCH_PATH = ROOT / "docs/evidence/ai-bench-001/alice-final-run-7-summary.json"
PROVIDER = "yandex-alice-ai-llm"
TASKS = ("resume_analysis", "vacancy_match", "cover_letter", "interview_questions")
GATES = (
    "owner_strategy_approval", "legal001_consent_and_processing",
    "ai001_runtime_controls_and_tests", "production_source_ip_transport",
    "billing_account_and_quotas_verified", "model_uri_recorded_and_evaluation_compatible",
    "no_logging_confirmed_after_wait", "data_location_and_backups_approved",
)


class PolicyError(ValueError):
    """Safe error: messages contain field paths, never input values or secrets."""


def _exact(expected: Any) -> Callable[[Any], bool]:
    def equal(value: Any, target: Any = expected) -> bool:
        if type(value) is not type(target):
            return False
        if isinstance(target, list):
            return len(value) == len(target) and all(equal(v, t) for v, t in zip(value, target))
        return value == target
    return equal


def _integer(low: int, high: int) -> Callable[[Any], bool]:
    return lambda value: type(value) is int and low <= value <= high


def _decimal(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 24:
        return False
    # No exponents, signs, whitespace, NaN or Infinity in money configuration.
    import re
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        return False
    try:
        number = Decimal(value)
        return number.is_finite() and Decimal(0) < number <= Decimal("1000000")
    except InvalidOperation:
        return False


def _iso_date(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


# Deliberately closed specification: changes to capabilities require review/tests.
SCHEMA: dict[str, Any] = {
    "schema_version": _exact("1.0"), "package": _exact("AI-PROVIDER-001"),
    "policy_version": _exact("1.1.0"), "checked_on": _iso_date,
    "scope": _exact("offline_architecture_specification"),
    "owner_approval": _exact("approved"), "runtime_activation": _exact(False),
    "primary": {
        "provider_id": _exact(PROVIDER), "model_family": _exact("aliceai-llm"),
        "observed_model_alias": _exact("aliceai-llm/latest"),
        "immutable_model_revision": _exact(None),
        "endpoint": _exact("https://ai.api.cloud.yandex.net/v1/chat/completions"),
        "transport": _exact("synchronous_json_schema"),
        "api_key_env": _exact("AI_YANDEX_API_KEY"),
        "folder_id_env": _exact("AI_YANDEX_FOLDER_ID"),
        "model_uri_env": _exact("AI_YANDEX_MODEL_URI"),
        "required_headers": {"x-data-logging-enabled": _exact("false")},
        "qualification_artifact": _exact("34830877796"),
        "qualification_dataset": _exact("1.3.6"),
        "qualification_contract": _exact("grounded-v2.6.1"),
    },
    "routing": {
        "planned_markets": _exact(["RU", "BY"]), "enabled_markets": _exact([]),
        "languages": _exact(["ru", "en"]),
        "tasks": {task: _exact(PROVIDER) for task in TASKS},
        "unknown_route": _exact("deny"), "cross_provider_fallback": _exact(False),
        "fallback": _exact("manual_without_generation"),
        "fallback_user_notice_required": _exact(True),
        "fallback_user_notice_key": _exact("ai_temporarily_unavailable_manual_mode"),
        "manual_mode_features": _exact(["vacancy_search", "career_profile", "resume_editor"]),
        "candidate_models_pending_qualification": _exact(["aliceai-llm-flash", "yandexgpt-pro-5.1"]),
        "local_model": _exact(None),
    },
    "privacy": {
        **{field: _exact(False) for field in (
            "request_body_logging", "response_body_logging", "cross_user_cache",
            "provider_tools", "provider_files", "provider_async", "real_personal_data_allowed_now")},
        "content_retention_days": _exact(0),
        "content_retention_scope": _exact("application_diagnostic_copies_only_not_user_owned_saved_documents"),
        "usage_metadata_retention_days": _integer(1, 30),
        "provider_metadata_retention": _exact("unconfirmed"),
        "no_logging_min_wait_hours": _integer(24, 168),
        "no_logging_effective_at": _exact(None),
        "allowed_input": _exact(["confirmed_relevant_profile_facts", "bounded_public_vacancy_facts", "explicit_user_task", "task_local_evidence_ids"]),
        "excluded_input": _exact(["credentials", "contact_identifiers", "address", "birth_date", "photos", "protected_secrets", "special_category_data", "biometric_data", "raw_pdf", "unconfirmed_profile_facts", "provider_oauth_payloads"]),
        "save_generated_document": _exact("explicit_owner_action_no_profile_fact_promotion"),
    },
    "limits": {
        "max_input_tokens": _integer(1, 8000), "max_output_tokens": _integer(1, 1600),
        "max_attempts": _integer(1, 2), "max_global_concurrency": _integer(1, 2),
        "max_user_concurrency": _exact(1), "per_attempt_timeout_seconds": _integer(1, 25),
        "total_timeout_seconds": _integer(1, 55), "max_retry_delay_seconds": _integer(0, 2),
        "user_daily_requests": _integer(1, 100), "global_daily_requests": _integer(1, 1000),
        "user_daily_budget_rub": _decimal, "global_daily_budget_rub": _decimal,
        "global_monthly_budget_rub": _decimal,
        "budget_status": _exact("internal_beta_safety_guard_not_commercial_entitlement_not_runtime_enforced"),
        "configuration_target": _exact("central_server_side_quota_policy"),
        "provider_adapter_must_not_embed_commercial_limits": _exact(True),
    },
    "commercial_access": {
        "status": _exact("architecture_reserved_not_runtime_enforced"),
        "launch_tiers": _exact(["free", "standard"]),
        "reserved_tiers": _exact(["max"]),
        "commercial_quota_values": _exact(None),
        "user_visible_meter": _exact("feature_actions_not_tokens"),
        "tokens_user_visible": _exact(False),
        "free_goal": _exact("complete_small_value_loop_then_conversion"),
        "standard_goal": _exact("normal_active_job_search_without_micro_metering"),
        "max_goal": _exact("reserved_for_heavy_usage_after_observed_demand"),
        "runtime_entitlement_architecture_package": _exact("AI-001"),
        "commercial_quota_definition_package": _exact("BILL-001"),
        "failed_generation_consumes_user_entitlement": _exact(False),
    },
    "failure_policy": {
        "retry_http_statuses": _exact([429, 502, 503, 504]),
        "no_retry_reasons": _exact(["auth_failure", "permission_denied", "model_retired", "invalid_request", "safety_refusal", "schema_failure", "grounding_failure", "read_timeout_unknown_outcome"]),
        "unknown_usage": _exact("retain_reservation_until_reconciled"),
        "ledger_unavailable": _exact("deny"), "budget_exhausted": _exact("deny"),
        "circuit_breaker_consecutive_failures": _integer(1, 3),
        "circuit_breaker_cooldown_seconds": _integer(60, 3600),
        "circuit_half_open_max_calls": _exact(1),
    },
    "pricing": {
        "checked_on": _iso_date, "valid_for_days": _integer(1, 30),
        "unit_tokens": _exact(1000), "mode": _exact("synchronous_no_tools"),
        "RUB": {"input": _decimal, "output": _decimal, "vat": _exact("included")},
        "USD": {"input": _decimal, "output": _decimal, "vat": _exact("excluded")},
        "cache_discount_assumed": _exact(False), "source_id": _exact("S1"),
    },
    "activation_gates": _exact(list(GATES)),
    "future_environment": {"AI_ENABLED": _exact("0"), "AI_KILL_SWITCH": _exact("1"), "AI_PRIMARY_PROVIDER": _exact(PROVIDER)},
}


def validate_policy(policy: Any) -> list[str]:
    errors: list[str] = []
    def visit(value: Any, shape: Any, path: str) -> None:
        if isinstance(shape, dict):
            if not isinstance(value, dict):
                errors.append(f"{path}: expected object")
                return
            if set(value) != set(shape):
                errors.append(f"{path}: unexpected or missing fields")
            for key, child in shape.items():
                if key in value:
                    visit(value[key], child, f"{path}.{key}")
        elif not shape(value):
            errors.append(f"{path}: violates policy constraint")
    visit(policy, SCHEMA, "policy")
    if errors:
        return errors
    limits = policy["limits"]
    minimum_deadline = (limits["max_attempts"] * limits["per_attempt_timeout_seconds"]
                        + (limits["max_attempts"] - 1) * limits["max_retry_delay_seconds"])
    if limits["total_timeout_seconds"] < minimum_deadline:
        errors.append("policy.limits: total deadline cannot cover proposed attempts")
    budgets = [Decimal(limits[k]) for k in ("user_daily_budget_rub", "global_daily_budget_rub", "global_monthly_budget_rub")]
    if budgets != sorted(budgets):
        errors.append("policy.limits: budgets must be ordered user <= daily <= monthly")
    if limits["user_daily_requests"] > limits["global_daily_requests"]:
        errors.append("policy.limits: request limits are inconsistent")
    if policy["pricing"]["checked_on"] > policy["checked_on"]:
        errors.append("policy.pricing: check date is after policy date")
    return errors


def _require_valid(policy: Any) -> None:
    errors = validate_policy(policy)
    if errors:
        raise PolicyError("; ".join(errors))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError("policy JSON contains duplicate fields")
        result[key] = value
    return result


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        if path.stat().st_size > 65536:
            raise PolicyError("policy JSON exceeds size limit")
        policy = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PolicyError("policy file is unavailable or invalid JSON") from exc
    _require_valid(policy)
    return policy


def quote_cost(policy: dict[str, Any], input_tokens: int, output_tokens: int,
               *, currency: str = "RUB", attempts: int = 1) -> Decimal:
    """Exact price-snapshot calculation; not a billing quote or token estimator."""
    _require_valid(policy)
    if not all(type(n) is int and 0 <= n <= 1000000 for n in (input_tokens, output_tokens)):
        raise PolicyError("token counts must be bounded non-negative integers")
    if type(attempts) is not int or not 1 <= attempts <= policy["limits"]["max_attempts"]:
        raise PolicyError("attempt count exceeds approved planning bound")
    if currency not in ("RUB", "USD"):
        raise PolicyError("currency is not in the price snapshot")
    prices = policy["pricing"][currency]
    return (Decimal(input_tokens) * Decimal(prices["input"])
            + Decimal(output_tokens) * Decimal(prices["output"])) / Decimal(1000) * attempts


def pricing_is_current(policy: dict[str, Any], as_of: date) -> bool:
    _require_valid(policy)
    age = (as_of - date.fromisoformat(policy["pricing"]["checked_on"])).days
    return 0 <= age < policy["pricing"]["valid_for_days"]


def route_preview(policy: dict[str, Any], task: str, language: str, market: str) -> dict[str, Any]:
    """Describe the plan. This API can NEVER authorize a provider call."""
    _require_valid(policy)
    if not all(isinstance(value, str) for value in (task, language, market)):
        raise PolicyError("route fields must be strings")
    known = (task in policy["routing"]["tasks"] and language in policy["routing"]["languages"]
             and market in policy["routing"]["planned_markets"])
    return {"planned_provider": PROVIDER if known else None, "provider_call_allowed": False,
            "reason": "runtime_not_implemented_or_approved" if known else "unsupported_route",
            "fallback": "manual_without_generation",
            "fallback_user_notice_required": True,
            "fallback_user_notice_key": policy["routing"]["fallback_user_notice_key"]}


def cost_report(policy: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    _require_valid(policy)
    if evidence.get("run_id") != "ai-bench-20260914T100639Z-222dfc87":
        raise PolicyError("unexpected benchmark cost evidence")
    cases = evidence.get("cases", [])
    if len(cases) != 8 or len({c["case_id"] for c in cases}) != 8:
        raise PolicyError("expected eight distinct benchmark cases")
    rows = []
    for case in cases:
        i, o = case["usage"]["input_tokens"], case["usage"]["output_tokens"]
        rows.append({"case_id": case["case_id"], "task": case["task"], "input_tokens": i,
                     "output_tokens": o, "rub_including_vat": str(quote_cost(policy, i, o)),
                     "usd_excluding_vat": str(quote_cost(policy, i, o, currency="USD"))})
    total_rub = sum((Decimal(row["rub_including_vat"]) for row in rows), Decimal(0))
    total_usd = sum((Decimal(row["usd_excluding_vat"]) for row in rows), Decimal(0))
    limits = policy["limits"]
    scenarios = []
    for name, i, o in (("sparse_profile_example",1000,300), ("richer_profile_assumption",4000,700),
                       ("input_and_output_cap",limits["max_input_tokens"],limits["max_output_tokens"])):
        scenarios.append({"name":name,"input_tokens":i,"output_tokens":o,
                          "one_attempt_rub":str(quote_cost(policy,i,o)),
                          "max_attempts_reserve_rub":str(quote_cost(policy,i,o,attempts=limits["max_attempts"])),
                          "1000_one_attempt_jobs_rub":str(quote_cost(policy,i,o)*1000)})
    # Owner planning scenario: three resumes, ten AI-reviewed vacancies per resume,
    # and four-to-five letters per resume. Assumptions are planning inputs, not measured averages.
    resume_calls = 6  # 3 resumes x initial generation + one refinement
    match_calls = 30  # 3 resumes x 10 shortlisted vacancies
    letter_calls_low, letter_calls_high = 12, 15
    resume_one = quote_cost(policy, 4000, 1200)
    match_one = quote_cost(policy, 2000, 300)
    letter_one = quote_cost(policy, 3000, 450)
    base_low = resume_one * resume_calls + match_one * match_calls + letter_one * letter_calls_low
    base_high = resume_one * resume_calls + match_one * match_calls + letter_one * letter_calls_high
    buffer = Decimal("1.20")
    heavy_user_scenario = {
        "label":"three_resumes_30_matches_12_to_15_letters",
        "assumptions":{"resume_calls":resume_calls,"resume_tokens_each":{"input":4000,"output":1200},
                       "match_calls":match_calls,"match_tokens_each":{"input":2000,"output":300},
                       "letter_calls":{"min":letter_calls_low,"max":letter_calls_high},
                       "letter_tokens_each":{"input":3000,"output":450},"operational_buffer_percent":20},
        "rub":{"base_min":str(base_low),"base_max":str(base_high),
               "with_buffer_min":str(base_low*buffer),"with_buffer_max":str(base_high*buffer)},
        "interpretation":"planning illustration only; commercial quotas remain unset"
    }
    return {"schema_version":"1.1","basis":"provider-reported synthetic usage; prices checked 2026-09-14; not production workload or an invoice",
            "artifact":"34830877796","cases":rows,"totals":{"input_tokens":sum(r["input_tokens"] for r in rows),
            "output_tokens":sum(r["output_tokens"] for r in rows),"rub_including_vat":str(total_rub),
            "usd_excluding_vat":str(total_usd)},"scenarios":scenarios,"heavy_user_scenario":heavy_user_scenario,
            "technical_guards":{"user_daily_budget_rub":limits["user_daily_budget_rub"],
                                "global_daily_budget_rub":limits["global_daily_budget_rub"],
                                "global_monthly_budget_rub":limits["global_monthly_budget_rub"],
                                "commercial_entitlement":False},
            "excluded_costs":["hosting","database","tools","future storage","payment processing","additional taxes where applicable"],
            "provider_call_allowed":False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--cost-report", action="store_true")
    args = parser.parse_args()
    try:
        policy = load_policy(args.policy)
        if args.cost_report:
            result = cost_report(policy, json.loads(BENCH_PATH.read_text(encoding="utf-8")))
        else:
            result = {"ok":True,"package":policy["package"],"scope":policy["scope"],"runtime_activation":False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (PolicyError, OSError, KeyError, TypeError, ValueError) as exc:
        # Do not print arbitrary JSON values, paths, exception traces or credentials.
        print(json.dumps({"ok":False,"error":str(exc) if isinstance(exc, PolicyError) else "invalid cost evidence"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
