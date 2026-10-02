import json

import pytest

from scripts.check_job003_package import (
    AUTHORIZED_GUARD_CHANGES,
    EVIDENCE,
    NEW_RUNTIME,
    REVIEWED_RUNTIME_CHANGES,
    ROOT,
    successor_hashes,
    validate,
)


def test_job003_package_guard_and_exact_evidence_sets():
    evidence = json.loads((ROOT / EVIDENCE).read_text())
    assert set(evidence['reviewed_runtime_changes']) == REVIEWED_RUNTIME_CHANGES
    assert set(evidence['new_runtime_sha256']) == NEW_RUNTIME
    assert set(evidence['authorized_guard_changes']) == AUTHORIZED_GUARD_CHANGES
    assert validate() == []


@pytest.mark.parametrize('section', [
    'reviewed_runtime_changes', 'new_runtime_sha256', 'authorized_guard_changes',
])
def test_job003_guard_rejects_extra_authorized_path_before_hash_consumption(tmp_path, section):
    path = tmp_path / EVIDENCE
    path.parent.mkdir(parents=True)
    evidence = json.loads((ROOT / EVIDENCE).read_text())
    evidence[section]['arbitrary/future_protected.py'] = (
        '0' * 64 if section == 'new_runtime_sha256'
        else {'previous_sha256': '0' * 64, 'current_sha256': '0' * 64}
    )
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match='scope:' + section):
        successor_hashes(tmp_path)
