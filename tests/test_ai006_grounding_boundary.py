from pathlib import Path
import json
import shutil

from scripts.check_ai006_grounding_boundary import CONTRACT, EVIDENCE, validate

ROOT = Path(__file__).resolve().parents[1]


def _copy(tmp_path):
    for relative in (CONTRACT, EVIDENCE):
        target=tmp_path/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/relative,target)


def test_grounding_successor_boundary_is_exact():
    assert validate(ROOT) == []


def test_grounding_successor_rejects_contract_tampering(tmp_path):
    _copy(tmp_path)
    contract=tmp_path/CONTRACT
    contract.write_text(contract.read_text()+'\n# unreviewed\n')
    assert validate(tmp_path) == ['AI-006 grounding hardening successor boundary is not verified']


def test_grounding_successor_rejects_predecessor_or_safety_metadata_tampering(tmp_path):
    for key,value in [('previous_sha256','0'*64),('provider_calls',1)]:
        _copy(tmp_path);path=tmp_path/EVIDENCE;data=json.loads(path.read_text())
        if key == 'previous_sha256':
            data['reviewed_runtime_changes'][CONTRACT][key]=value
        else:
            data[key]=value
        path.write_text(json.dumps(data))
        assert validate(tmp_path) == ['AI-006 grounding hardening successor boundary is not verified']
