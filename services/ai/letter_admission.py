"""No legal approval is fabricated by a boolean, environment flag or form.

The deployed application's admission policy denies all real/user-supplied data.
The test admission is injectable only in code and compares the entire projected
payload to an immutable synthetic manifest. It is not installed by app.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

from domain.cover_letter import LetterError, digest
from services.ai.letter_contract import LetterContract


class ClosedLetterAdmission:
    def check(self, *, user_id: str, letter_id: str, contract: LetterContract,
              now: int, session=None) -> str:
        raise LetterError('generation_unavailable')


# Filled from the shipped source-only synthetic cases; changing the file requires
# a reviewed code change, not an arbitrary client "synthetic=true" assertion.
SYNTHETIC_MANIFEST_SHA256 = '2a1068724e70646e56d902f50cc06a8a9b4db0307617194c4ad16317766c6005'
SYNTHETIC_PATH = Path(__file__).with_name('letter_synthetic_cases.json')


def synthetic_cases() -> dict:
    raw = SYNTHETIC_PATH.read_bytes()
    if hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()!=SYNTHETIC_MANIFEST_SHA256:
        raise LetterError('invalid_source')
    value = json.loads(raw)
    if value.get('scope')!='synthetic_only' or value.get('version')!=1:
        raise LetterError('invalid_source')
    return value['cases']


@dataclass(frozen=True, slots=True)
class SyntheticLetterAdmission:
    """For an isolated synthetic runner only. Never selected by deployment flags."""
    owner_id: str = field(repr=False)

    def check(self, *, user_id: str, letter_id: str, contract: LetterContract,
              now: int, session=None) -> str:
        if user_id != self.owner_id:
            raise LetterError('generation_unavailable')
        # Compare full content, not just a caller-supplied hash or fixture name.
        projected = contract.projection
        matches = any(projected['candidate_facts']==case['candidate_facts']
                      and projected['vacancy']==case['vacancy']
                      for case in synthetic_cases().values())
        if not matches or contract.payload_hash!=digest(projected):
            raise LetterError('generation_unavailable')
        return 'synthetic-test-only-v1'
