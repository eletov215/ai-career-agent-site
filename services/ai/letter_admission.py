"""LEGAL-001-aware cover-letter admission.

User consent and production legal-policy activation are independent server-side
gates. The current reviewed-code policy is DRAFT and domain REAL_DATA_SUPPORTED
remains false, so deployed real-data Alice traffic stays fail-closed regardless
of environment variables or client form fields.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

from domain.ai import PROVIDER, REAL_DATA_SUPPORTED
from domain.cover_letter import LetterError, digest
from services.ai.letter_contract import CONTRACT_VERSION, LetterContract
from services.consent import ConsentNotActiveError, ConsentService


class ClosedLetterAdmission:
    def check(self, *, user_id: str, letter_id: str, contract: LetterContract,
              now: int, session=None) -> str:
        raise LetterError("generation_unavailable")


@dataclass(frozen=True, slots=True)
class LegalLetterAdmission:
    consent_service: ConsentService = field(repr=False)

    def check(self, *, user_id: str, letter_id: str, contract: LetterContract,
              now: int, session=None) -> str:
        policy = self.consent_service.policy
        if policy.provider != PROVIDER or contract.version != CONTRACT_VERSION:
            raise LetterError("generation_unavailable")
        try:
            consent = self.consent_service.require_current_acceptance(user_id, session=session)
        except ConsentNotActiveError:
            raise LetterError("generation_unavailable") from None
        if not policy.production_active or not REAL_DATA_SUPPORTED:
            raise LetterError("generation_unavailable")
        return f"legal001:{policy.version}:{consent['id']}"


SYNTHETIC_MANIFEST_SHA256 = "2a1068724e70646e56d902f50cc06a8a9b4db0307617194c4ad16317766c6005"
SYNTHETIC_PATH = Path(__file__).with_name("letter_synthetic_cases.json")


def synthetic_cases() -> dict:
    raw = SYNTHETIC_PATH.read_bytes()
    if hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() != SYNTHETIC_MANIFEST_SHA256:
        raise LetterError("invalid_source")
    value = json.loads(raw)
    if value.get("scope") != "synthetic_only" or value.get("version") != 1:
        raise LetterError("invalid_source")
    return value["cases"]


@dataclass(frozen=True, slots=True)
class SyntheticLetterAdmission:
    """For an isolated synthetic runner only. Never selected by deployment flags."""
    owner_id: str = field(repr=False)

    def check(self, *, user_id: str, letter_id: str, contract: LetterContract,
              now: int, session=None) -> str:
        if user_id != self.owner_id:
            raise LetterError("generation_unavailable")
        projected = contract.projection
        matches = any(
            projected["candidate_facts"] == case["candidate_facts"]
            and projected["vacancy"] == case["vacancy"]
            for case in synthetic_cases().values()
        )
        if not matches or contract.payload_hash != digest(projected):
            raise LetterError("generation_unavailable")
        return "synthetic-test-only-v1"
