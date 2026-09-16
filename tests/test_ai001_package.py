from pathlib import Path
import json,shutil
import subprocess,sys
import pytest
from scripts.check_ai001_package import validate,load_boundary,ROOT

def test_ai001_package_complete_and_closed():
    assert validate()==[]

def test_missing_package_is_not_accepted(tmp_path):
    assert validate(tmp_path)

def test_protected_runtime_changes_require_current_hash(tmp_path):
    for rel in ('docs/evidence/ai-001/change_boundary.json','docs/evidence/ai-provider-001/preserved_files_sha256.json'):
        (tmp_path/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,tmp_path/rel)
    rows=json.loads((tmp_path/'docs/evidence/ai-001/change_boundary.json').read_text())['reviewed_runtime_changes']
    for rel in rows:
        (tmp_path/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,tmp_path/rel)
    rel='docs/evidence/ai-002/change_boundary.json'
    (tmp_path/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,tmp_path/rel)
    extra=json.loads((ROOT/rel).read_text())['reviewed_runtime_changes']
    for name in extra:
        (tmp_path/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,tmp_path/name)
    for relative in ('docs/evidence/ai-003/change_boundary.json', 'docs/evidence/ai-003/baseline_files_sha256.json', 'docs/evidence/ai-001/change_boundary.json', 'docs/evidence/ai-004/change_boundary.json', 'docs/evidence/ai-004/baseline_files_sha256.json'):
        (tmp_path/relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, tmp_path/relative)
    successor = json.loads((ROOT/'docs/evidence/ai-003/change_boundary.json').read_text())['reviewed_runtime_changes']
    for relative in successor:
        (tmp_path/relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, tmp_path/relative)
    assert load_boundary(tmp_path)
    (tmp_path/'app.py').write_text('unreviewed runtime replacement')
    with pytest.raises(ValueError):load_boundary(tmp_path)

def test_no_accepted_benchmark_path_can_be_superseded(tmp_path):
    for rel in ('docs/evidence/ai-001/change_boundary.json','docs/evidence/ai-provider-001/preserved_files_sha256.json'):
        (tmp_path/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,tmp_path/rel)
    f=tmp_path/'docs/evidence/ai-001/change_boundary.json';d=json.loads(f.read_text());d['reviewed_runtime_changes']['evals/ai_bench/scoring.py']={'previous_sha256':'a','current_sha256':'b'};f.write_text(json.dumps(d))
    with pytest.raises(ValueError):load_boundary(tmp_path)


def test_benchmark_rejects_runtime_imports(tmp_path):
    from scripts.check_ai_bench_package import validate_runtime_separation
    (tmp_path/'evals').mkdir();(tmp_path/'evals/bad.py').write_text('from services.ai.service import AIService')
    with pytest.raises(SystemExit):validate_runtime_separation(tmp_path)


def test_benchmark_rejects_unqualified_runtime(tmp_path):
    from scripts.check_ai_bench_package import validate_runtime_separation
    (tmp_path/'services/ai').mkdir(parents=True)
    with pytest.raises(SystemExit):validate_runtime_separation(tmp_path)


def test_ai001_checker_stays_dependency_free_for_isolated_benchmark_gate():
    code = r"""
import builtins
real_import = builtins.__import__
def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split('.', 1)[0] in {'sqlalchemy', 'flask', 'alembic', 'psycopg'}:
        raise RuntimeError('forbidden runtime dependency import: ' + name)
    return real_import(name, globals, locals, fromlist, level)
builtins.__import__ = guarded
from scripts.check_ai001_package import validate
assert validate() == []
"""
    completed = subprocess.run(
        [sys.executable, '-c', code], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
