"""AI004-M04A: provider-free, owner-scoped cache and idempotency fingerprints.

This is *not* persistence or an admission switch. Caller must first obtain
sources through owner-qualified reads, build M03 ClassificationContract, and
verify source completeness and the independent legal gate. No database, HTTP,
provider, tokens, logs, or environment access occurs in this module.

Cache identity is stable for an owner, chosen immutable resume version, stable
vacancy identity, source contents and all scoring/classification versions.
A separate owner-action operation hash prevents duplicate dispatch/retries.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import UUID

from domain.vacancy_match import MATCH_VERSION
from services.matching_contract import (
    CLASSIFICATION_VERSION,
    ClassificationContract,
)

CACHE_KEY_VERSION = "ai004-owner-match-cache-v1"
_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_OPERATION_NONCE = re.compile(r"[A-Za-z0-9:_-]{8,128}\Z")


class MatchCacheKeyError(ValueError):
    """Fixed safe code only; never echo source text or personal identifiers."""


@dataclass(frozen=True, slots=True)
class MatchCacheAddress:
    """Opaque tokens only; exclude even fingerprints from accidental repr/logs."""

    cache_key_hash: str = field(repr=False)
    request_hash: str = field(repr=False)
    source_hash: str = field(repr=False)
    resume_hash: str = field(repr=False)
    vacancy_hash: str = field(repr=False)
    version: str = CACHE_KEY_VERSION


def _secret_bytes(secret: bytes) -> bytes:
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise MatchCacheKeyError("cache_key_unavailable")
    return secret


def _digest(value: Any) -> str:
    if not isinstance(value, str) or _HEX_64.fullmatch(value) is None:
        raise MatchCacheKeyError("invalid_cache_source")
    return value


def _uuid(value: Any) -> str:
    if not isinstance(value, str):
        raise MatchCacheKeyError("invalid_cache_source")
    try:
        if str(UUID(value)) != value:
            raise ValueError("not canonical")
    except (TypeError, ValueError, AttributeError):
        raise MatchCacheKeyError("invalid_cache_source") from None
    return value


def _mac(secret: bytes, label: str, value: Any) -> str:
    try:
        source = json.dumps([CACHE_KEY_VERSION, label, value],
                            ensure_ascii=False, separators=(",", ":"),
                            sort_keys=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        raise MatchCacheKeyError("invalid_cache_source") from None
    return hmac.new(secret, source, hashlib.sha256).hexdigest()


def build_cache_address(
    *,
    secret: bytes,
    user_id: str,
    resume_version_id: str,
    vacancy_identity_hash: str,
    contract: ClassificationContract,
) -> MatchCacheAddress:
    """Create opaque keys after source and ownership verification.

    vacancy_identity_hash MUST come from a trusted SEARCH stable_key or JOB-001
    provider identity_hash, not an arbitrary client-supplied identifier.
    The M03 source_hash binds projected content, requirement set and policies.
    Only trusted backend construction of a contract is permitted.
    """
    key = _secret_bytes(secret)
    owner = _uuid(user_id)
    version = _uuid(resume_version_id)
    vacancy = _digest(vacancy_identity_hash)
    if (not isinstance(contract, ClassificationContract)
            or contract.version != CLASSIFICATION_VERSION):
        raise MatchCacheKeyError("invalid_cache_source")
    combined = _digest(contract.source_hash)
    resume_hash = _digest(contract.resume_hash)
    vacancy_hash = _digest(contract.vacancy_hash)
    if not contract.requirements or not contract.candidate_facts:
        raise MatchCacheKeyError("invalid_cache_source")
    payload = {
        "owner_id": owner,
        "resume_version_id": version,
        "vacancy_identity_hash": vacancy,
        "contract_source_hash": combined,
        "resume_content_hash": resume_hash,
        "vacancy_content_hash": vacancy_hash,
        "classification_version": CLASSIFICATION_VERSION,
        "scoring_version": MATCH_VERSION,
    }
    return MatchCacheAddress(
        cache_key_hash=_mac(key, "cache", payload),
        request_hash=_mac(key, "request", payload),
        source_hash=combined,
        resume_hash=resume_hash,
        vacancy_hash=vacancy_hash,
    )


def build_operation_hash(*, secret: bytes, address: MatchCacheAddress,
                         owner_action_nonce: str) -> str:
    """Deduplicate a *single* approved user action independently of cache hits.

    Repeated nonce -> exactly the same ledger operation. A different nonce may
    be admitted ONLY when M05 preflight has ruled out an existing ready,
    pending or unknown charge and the user explicitly requested a new action.
    """
    key = _secret_bytes(secret)
    if (not isinstance(address, MatchCacheAddress)
            or address.version != CACHE_KEY_VERSION):
        raise MatchCacheKeyError("invalid_cache_source")
    address_key = _digest(address.cache_key_hash)
    if (not isinstance(owner_action_nonce, str)
            or _OPERATION_NONCE.fullmatch(owner_action_nonce) is None):
        raise MatchCacheKeyError("invalid_operation_nonce")
    return _mac(key, "operation", {
        "cache_key_hash": address_key,
        "owner_action_nonce": owner_action_nonce,
    })


def _check_validated_result(address: MatchCacheAddress,
                            report: Mapping[str, Any]) -> None:
    """Shape/link check, NOT independent semantic re-validation of M03 claims."""
    if (not isinstance(address, MatchCacheAddress)
            or address.version != CACHE_KEY_VERSION
            or not isinstance(report, Mapping)
            or set(report) != {
                "classification_version", "source_hash", "resume_hash",
                "vacancy_hash", "summary", "requirements", "presentation",
            }):
        raise MatchCacheKeyError("invalid_saved_report")
    if (report["classification_version"] != CLASSIFICATION_VERSION
            or report["source_hash"] != address.source_hash
            or report["resume_hash"] != address.resume_hash
            or report["vacancy_hash"] != address.vacancy_hash
            or report["presentation"] != "source_quotes_and_code_labels"):
        raise MatchCacheKeyError("invalid_saved_report")
    summary = report["summary"]
    if (not isinstance(summary, Mapping)
            or summary.get("policy_version") != MATCH_VERSION
            or type(summary.get("score_percent")) is not int
            or not 0 <= summary["score_percent"] <= 100
            or not isinstance(report["requirements"], list)
            or not report["requirements"]):
        raise MatchCacheKeyError("invalid_saved_report")


def seal_validated_result(*, secret: bytes, address: MatchCacheAddress,
                          report: Mapping[str, Any]) -> str:
    """Authenticate persisted bytes after M03.validate_classification succeeded.

    This MAC detects stored-result changes; it does not replace the M03
    source-grounding validator or the M04B owner-bound repository checks.
    """
    key = _secret_bytes(secret)
    _check_validated_result(address, report)
    return _mac(key, "validated_report", {
        "cache_key_hash": _digest(address.cache_key_hash),
        "report": report,
    })


def verify_sealed_result(*, secret: bytes, address: MatchCacheAddress,
                         report: Mapping[str, Any], signature: str) -> bool:
    """Fail closed: never serve a cache entry with invalid contents/signature."""
    try:
        if not isinstance(signature, str) or _HEX_64.fullmatch(signature) is None:
            return False
        expected = seal_validated_result(
            secret=secret, address=address, report=report,
        )
        return hmac.compare_digest(expected, signature)
    except (MatchCacheKeyError, TypeError, ValueError):
        return False
