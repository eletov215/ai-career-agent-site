import json
import pytest
from scripts.check_job004_package import EVIDENCE, NEW_RUNTIME, REVIEWED_RUNTIME, ROOT, SUPPORT, successor_hashes, validate

def test_job004_exact_package_boundary():
    evidence=json.loads((ROOT/EVIDENCE).read_text())
    assert set(evidence['reviewed_runtime_changes'])==REVIEWED_RUNTIME
    assert set(evidence['new_runtime_sha256'])==NEW_RUNTIME
    assert set(evidence['support_sha256'])==SUPPORT
    assert validate()==[]

@pytest.mark.parametrize('section',['reviewed_runtime_changes','new_runtime_sha256','support_sha256'])
def test_job004_rejects_extra_path(tmp_path,section):
    path=tmp_path/EVIDENCE;path.parent.mkdir(parents=True)
    evidence=json.loads((ROOT/EVIDENCE).read_text())
    evidence[section]['future/path']={'previous_sha256':'0'*64,'current_sha256':'0'*64} if section=='reviewed_runtime_changes' else '0'*64
    path.write_text(json.dumps(evidence))
    with pytest.raises(ValueError,match='scope:'+section): successor_hashes(tmp_path)
