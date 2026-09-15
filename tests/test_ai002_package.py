from pathlib import Path
import json
import subprocess
import sys
import shutil
import pytest
from scripts.check_ai002_package import validate,load_boundary,ROOT

def test_rebuilt_package_gate_passes():assert validate()==[]
def test_missing_package_fails(tmp_path):assert validate(tmp_path)

def test_no_runtime_dependencies_for_all_package_gates():
    code="""
import builtins
original=builtins.__import__
def blocked(name,*args,**kwargs):
    if name.split('.')[0] in {'flask','sqlalchemy','alembic','psycopg'}:raise RuntimeError('runtime import')
    return original(name,*args,**kwargs)
builtins.__import__=blocked
from scripts.check_ai002_package import validate
from scripts.check_ai001_package import validate as ai001
from scripts.check_ai_provider_package import validate as provider
assert validate()==[]
assert ai001()==[]
assert provider()==[]
"""
    result=subprocess.run([sys.executable,'-S','-c',code],cwd=ROOT,text=True,capture_output=True)
    assert result.returncode==0,result.stdout+result.stderr

def test_successor_hashes_are_checked_and_cannot_whitelist_evals(tmp_path):
    for name in ['docs/evidence/ai-001/change_boundary.json','docs/evidence/ai-002/change_boundary.json']:
        (tmp_path/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,tmp_path/name)
    d=json.loads((ROOT/'docs/evidence/ai-002/change_boundary.json').read_text())
    for name in d['reviewed_runtime_changes']:
        (tmp_path/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,tmp_path/name)
    assert load_boundary(tmp_path)
    (tmp_path/'app.py').write_text('changed')
    with pytest.raises(ValueError):load_boundary(tmp_path)
    d['reviewed_runtime_changes']['evals/ai_bench/scoring.py']={'previous_sha256':'a','current_sha256':'b'}
    (tmp_path/'docs/evidence/ai-002/change_boundary.json').write_text(json.dumps(d))
    with pytest.raises(ValueError):load_boundary(tmp_path)

def test_reference_ui_has_no_generation_or_file_upload_input():
    source=(ROOT/'routes/resume_analysis.py').read_text()
    assert '.analyze(' not in source and '.generate(' not in source
    for path in (ROOT/'templates/analysis').glob('*.html'):
        source=path.read_text();assert '|safe' not in source and 'type="file"' not in source
        assert 'csrf_token' in source

def test_analysis_config_is_closed_by_default_and_not_aliased_to_ai_enabled():
    from config import load_settings
    from dataclasses import asdict
    s=load_settings({'APP_ENV':'test','DATA_DIR':'/tmp/ai002-config-only'})
    assert not s.ai_analysis_review_enabled
    s=load_settings({'APP_ENV':'test','DATA_DIR':'/tmp/ai002-config-only','AI_ANALYSIS_REVIEW_ENABLED':'1'})
    assert s.ai_analysis_review_enabled and not s.ai.enabled and s.ai.kill_switch and not s.ai.synthetic_access_enabled
