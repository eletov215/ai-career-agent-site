from pathlib import Path
import json
import shutil

from scripts.check_ai005_live_qa_boundary import CHANGES, EVIDENCE, successor_hashes, validate

ROOT = Path(__file__).resolve().parents[1]


def _copy(tmp_path):
    for relative in CHANGES | {EVIDENCE, 'scripts/check_ai005_live_qa_boundary.py', 'domain/ai.py'}:
        target = tmp_path/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, target)


def test_live_qa_successor_boundary_is_exact():
    assert validate(ROOT) == []
    assert set(successor_hashes(ROOT)) == CHANGES


def test_live_qa_successor_rejects_runtime_or_scope_tampering(tmp_path):
    _copy(tmp_path)
    assert validate(tmp_path) == []
    runtime = tmp_path/'services/ai/letter_runtime.py'
    runtime.write_text(runtime.read_text() + '\n# unreviewed\n')
    assert validate(tmp_path)
    _copy(tmp_path)
    evidence = tmp_path/EVIDENCE
    value = json.loads(evidence.read_text())
    value['paid_provider_calls'] = 1
    evidence.write_text(json.dumps(value))
    assert validate(tmp_path)


def test_live_qa_successor_rejects_changed_predecessor_hash(tmp_path):
    _copy(tmp_path)
    evidence = tmp_path/EVIDENCE
    value = json.loads(evidence.read_text())
    value['reviewed_runtime_changes']['services/ai/letter_runtime.py']['previous_sha256'] = '0' * 64
    evidence.write_text(json.dumps(value))
    assert validate(tmp_path) == ['AI-005 live QA successor boundary is not verified']
