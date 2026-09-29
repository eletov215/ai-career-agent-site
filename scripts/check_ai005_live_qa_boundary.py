#!/usr/bin/env python3
"""Explicit successor proof for AI-005 validation observability."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = 'docs/evidence/ai-005-live-qa-001/change_boundary.json'
SOURCE_COMMIT = 'c1b8f216868e77faaa679001d5861a0fb0886523'
SOURCE_TREE = 'efed1c142f252a714daebe3c976e44ee7439a507'
CHANGES = {
    'services/ai/letter_contract.py', 'services/ai/letter_runtime.py',
    'scripts/legal001_boundary.py', 'scripts/check_ai005_site_qa_package.py',
}
PREVIOUS = {
    'services/ai/letter_contract.py': 'b1ef9f4eb069b505e031c773c822d8abe280f8c96edd0d4d196887be96f563d6',
    'services/ai/letter_runtime.py': '93064769bbac637ad08b798a0436194ba611618a171ada25c3488ad2f8e34bbb',
    'scripts/legal001_boundary.py': '3245e76cab3d32d75256f3a2e151fc5a1bc3795e77772ddaf95c79dee984b4b6',
    'scripts/check_ai005_site_qa_package.py': '9df01c00e5cda463573d90474ea68762d03ce652f461bf719b3ca6a089b0af19',
}


def _matches(path: Path, expected: str) -> bool:
    raw = path.read_bytes()
    return expected in {hashlib.sha256(raw).hexdigest(),
                        hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()}


def successor_hashes(root: Path = ROOT) -> dict[str, str]:
    evidence = json.loads((root/EVIDENCE).read_text())
    rows = evidence.get('reviewed_runtime_changes', {})
    if (evidence.get('package') != 'AI-005-LIVE-QA-001'
            or evidence.get('release') != 'validation-observability-successor'
            or evidence.get('source_commit') != SOURCE_COMMIT
            or evidence.get('source_tree') != SOURCE_TREE
            or evidence.get('issue') != 54
            or evidence.get('public_real_data_enabled') is not False
            or evidence.get('legal_state') != 'DRAFT'
            or evidence.get('paid_provider_calls') != 0
            or set(rows) != CHANGES):
        raise ValueError('Invalid AI-005 live QA successor scope')
    for relative, row in rows.items():
        if (set(row) != {'previous_sha256', 'current_sha256'}
                or row['previous_sha256'] != PREVIOUS[relative]):
            raise ValueError('Invalid AI-005 live QA hash transition')
        if not _matches(root/relative, row['current_sha256']):
            raise ValueError('AI-005 live QA successor hash mismatch: ' + relative)
    contract = (root/'services/ai/letter_contract.py').read_text()
    runtime = (root/'services/ai/letter_runtime.py').read_text()
    if ('VALIDATION_REASONS = frozenset' not in contract
            or "raise LetterValidationError(reason)" not in contract
            or "else 'feature_validation_failure'" not in runtime
            or "if reason in VALIDATION_REASONS else reason" not in runtime):
        raise ValueError('AI-005 validation observability boundary is incomplete')
    return {relative: row['current_sha256'] for relative, row in rows.items()}


def validate(root: Path = ROOT) -> list[str]:
    try:
        successor_hashes(root)
        return []
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return ['AI-005 live QA successor boundary is not verified']


if __name__ == '__main__':
    errors = validate()
    print(json.dumps({'package':'AI-005-LIVE-QA-001', 'ok':not errors,
                      'provider_calls':0, 'errors':errors}, indent=2))
    raise SystemExit(bool(errors))
