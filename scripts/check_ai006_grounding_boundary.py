#!/usr/bin/env python3
"""Verify the additive candidate-fit grounding successor boundary."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = 'docs/evidence/ai-006-grounding-hardening/change_boundary.json'
CONTRACT = 'services/ai/letter_contract.py'
SOURCE_MAIN_SHA = 'ba7288518a3dab13878f610bbd9f8f6f38d66019'
PREVIOUS_SHA256 = '0cc6d87b2390b12c0145025819f85099175b30880e005e8a3a039618a9bffd86'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path = ROOT) -> list[str]:
    try:
        evidence = json.loads((root/EVIDENCE).read_text())
        rows = evidence.get('reviewed_runtime_changes', {})
        expected_metadata = {
            'package':'AI-006-GROUNDING-HARDENING',
            'release':'candidate-fit-grounding-successor',
            'source_main_sha':SOURCE_MAIN_SHA,
            'provider_calls':0,
            'REAL_DATA_SUPPORTED':False,
            'real_data_alice':'CLOSED',
            'legal_state':'DRAFT / NOT_ACTIVE',
            'production_schema':'unchanged',
        }
        if any(evidence.get(key) != value for key, value in expected_metadata.items()):
            raise ValueError('Invalid grounding successor metadata')
        if set(rows) != {CONTRACT}:
            raise ValueError('Invalid grounding successor scope')
        row = rows[CONTRACT]
        if (set(row) != {'previous_sha256','current_sha256'}
                or row['previous_sha256'] != PREVIOUS_SHA256
                or row['current_sha256'] != _sha256(root/CONTRACT)):
            raise ValueError('Invalid grounding hash transition')
        contract = (root/CONTRACT).read_text()
        required = (
            "'validation_candidate_claim_grounding'",
            "len(refs) != 1",
            "' '.join(prose.split()) != ' '.join(refs[0]['quote'].split())",
            'Each candidate_fit paragraph uses exactly one candidate fact.',
            'supporting candidate quote verbatim',
            'do not paraphrase candidate experience',
            'Use a separate candidate_fit paragraph for each additional fact.',
        )
        if not all(fragment in contract for fragment in required):
            raise ValueError('Grounding contract is incomplete')
        return []
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return ['AI-006 grounding hardening successor boundary is not verified']


if __name__ == '__main__':
    errors = validate()
    print(json.dumps({'package':'AI-006-GROUNDING-HARDENING', 'ok':not errors,
                      'provider_calls':0, 'errors':errors}, indent=2))
    raise SystemExit(bool(errors))
