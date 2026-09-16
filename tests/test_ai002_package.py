from pathlib import Path
import ast
import os
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
    for relative in ('docs/evidence/ai-003/change_boundary.json', 'docs/evidence/ai-003/baseline_files_sha256.json', 'docs/evidence/ai-001/change_boundary.json'):
        (tmp_path/relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, tmp_path/relative)
    successor = json.loads((ROOT/'docs/evidence/ai-003/change_boundary.json').read_text())['reviewed_runtime_changes']
    for relative in successor:
        (tmp_path/relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, tmp_path/relative)
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


def test_route_fixture_import_resolves_from_repository_root():
    """Regress the actual fixture import, even when Flask route tests are skipped.

    Run only the import statement from the shipped route test in a fresh Python
    process. This is not a replacement for running the Flask route suite in CI.
    """
    tree = ast.parse((ROOT / 'tests/test_ai002_routes.py').read_text())
    imports = [
        node for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and (node.module or '').endswith('test_ai002_service')
        and any(alias.name == 'env' for alias in node.names)
    ]
    assert len(imports) == 1, 'Expected exactly one shared AI-002 fixture import'
    code = (
        "__package__ = 'tests'\n"
        + ast.unparse(imports[0])
        + "\nassert callable(env)\nprint('fixture import: PASS')\n"
    )
    environment = os.environ.copy()
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(
        [sys.executable, '-c', code], cwd=ROOT, env=environment,
        text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'fixture import: PASS' in result.stdout


@pytest.mark.parametrize('statement', [
    'from test_ai002_service import env',
    'import test_ai002_service',
])
def test_static_gate_rejects_bare_sibling_test_imports(tmp_path, statement):
    from scripts.check_ai002_package import validate_test_imports as check_imports
    folder = tmp_path / 'tests'
    folder.mkdir()
    (folder / '__init__.py').write_text('')
    (folder / 'test_ai002_service.py').write_text('# AST inspection only\n')
    (folder / 'test_ai002_routes.py').write_text(statement + '\n')
    errors = check_imports(tmp_path)
    assert len(errors) == 1 and 'must be package-qualified' in errors[0]


@pytest.mark.parametrize('statement', [
    'from tests.test_ai002_service import env',
    'from .test_ai002_service import env',
    'import tests.test_ai002_service',
])
def test_static_gate_accepts_package_sibling_imports(tmp_path, statement):
    from scripts.check_ai002_package import validate_test_imports as check_imports
    folder = tmp_path / 'tests'
    folder.mkdir()
    (folder / '__init__.py').write_text('')
    (folder / 'test_ai002_service.py').write_text('# AST inspection only\n')
    (folder / 'test_ai002_routes.py').write_text(statement + '\n')
    assert check_imports(tmp_path) == []


def test_static_gate_requires_tests_package_marker(tmp_path):
    from scripts.check_ai002_package import validate_test_imports as check_imports
    folder = tmp_path / 'tests'
    folder.mkdir()
    assert check_imports(tmp_path) == ['Missing tests package marker: tests/__init__.py']


def test_review_template_shows_only_valid_actions_for_current_state():
    from jinja2 import DictLoader, Environment, FileSystemLoader, ChoiceLoader
    env = Environment(loader=ChoiceLoader([
        DictLoader({'base.html':'{% block content %}{% endblock %}'}),
        FileSystemLoader(str(ROOT / 'templates')),
    ]), autoescape=True)
    env.globals.update(url_for=lambda *a, **k: '/test', csrf_token=lambda: 'token')
    ui = {
        'title':'title','version':'version','reference':'reference','provider':'provider',
        'notice':'notice','strengths':'strengths','gaps':'gaps','gap_note':'gap_note',
        'recommendations':'recommendations','review_note':'review_note','source':'source',
        'fact':'fact','unverified':'unverified','review_history':'review_history',
        'delete':'delete','back':'back','accept':'accept','reject':'reject','reset':'reset',
        'pending':'pending','accepted':'accepted','rejected':'rejected',
    }
    base_report = {
        'id':'00000000-0000-0000-0000-000000000001','version':'1','origin':'reference','language':'ru',
        'source_hash':'hash','result':{
            'summary':'summary','strengths':[],'gaps':[],
            'recommendations':[{'action':'action','rationale':'rationale','evidence_ids':[]}],
            'facts_not_verified':[],
        },
        'source_facts':[],'review_events':[],
    }
    template = env.get_template('analysis/detail.html')
    for state, expected, forbidden in (
        ('pending', ('value="accepted"','value="rejected"'), ('value="pending"',)),
        ('accepted', ('value="pending"',), ('value="accepted"','value="rejected"')),
        ('rejected', ('value="pending"',), ('value="accepted"','value="rejected"')),
    ):
        report = dict(base_report)
        report['decisions'] = {'rec-1': {'decision':state,'revision':0}}
        html = template.render(ui=ui, report=report)
        form = html.split('<form method="post"', 1)[1].split('</form>', 1)[0]
        for marker in expected:
            assert marker in form
        for marker in forbidden:
            assert marker not in form
