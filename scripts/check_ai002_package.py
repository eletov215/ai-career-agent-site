#!/usr/bin/env python3
"""Dependency-free successor boundary for rebuilt AI-002. Never imports Flask/ORM."""
from pathlib import Path
import ast
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Explicitly reviewed runtime changes, never an arbitrary exclusion list.
CHANGES={
    'app.py','config.py','database.py','infra/vps/.env.example','models/__init__.py',
    'operations/backup.py','repositories/privacy.py','services/privacy.py',
    'services/storage.py','services/ai/service.py',
}
REQUIRED={
    'domain/resume_analysis.py','models/resume_analysis.py','repositories/resume_analysis.py',
    'services/resume_analysis.py','services/ai/analysis_validation.py',
    'routes/resume_analysis.py','templates/analysis/index.html','templates/analysis/detail.html',
    'static/resume_analysis.css','migrations/versions/20260915_0016_resume_analysis.py',
    'tests/test_ai002_service.py','tests/test_ai002_routes.py','tests/test_ai002_migration.py',
    'tests/test_ai002_package.py','docs/AI002_IMPLEMENTATION.md','docs/AI002_VERIFICATION_STATUS.md','docs/AI002_RUNBOOK.md',
}

def matches(path, expected):
    raw=path.read_bytes()
    return expected in {hashlib.sha256(raw).hexdigest(),hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()}

def load_boundary(root=ROOT):
    d=json.loads((root/'docs/evidence/ai-002/change_boundary.json').read_text())
    if d['package']!='AI-002' or d['public_real_data_enabled'] is not False or set(d['reviewed_runtime_changes'])!=CHANGES:
        raise ValueError('Invalid AI-002 scope')
    old=json.loads((root/'docs/evidence/ai-001/change_boundary.json').read_text())['reviewed_runtime_changes']
    successor = {}
    if (root/'docs/evidence/ai-003/change_boundary.json').is_file():
        from scripts.check_ai003_package import load_boundary as load_ai003_boundary
        successor = load_ai003_boundary(root)
    effective = {}
    for rel,item in d['reviewed_runtime_changes'].items():
        if rel in old and item['previous_sha256']!=old[rel]['current_sha256']:
            raise ValueError('AI-001 parent mismatch')
        current = successor.get(rel, item)['current_sha256']
        effective[rel] = {**item, 'current_sha256': current}
        if not matches(root/rel,current):
            raise ValueError('AI-002 runtime hash mismatch')
    return {**effective, **successor}

def validate_test_imports(root=ROOT):
    """Catch sibling test imports without importing Flask or executing test code."""
    directory = root / 'tests'
    errors = []
    if not (directory / '__init__.py').is_file():
        errors.append('Missing tests package marker: tests/__init__.py')
    for path in sorted(directory.glob('test_ai002*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                modules = [node.module or '']
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            else:
                continue
            for module in modules:
                top_level = module.split('.')[0]
                if top_level.startswith('test_') and (directory / (top_level + '.py')).is_file():
                    errors.append(
                        f'{path.name}:{node.lineno}: sibling test import {module!r} '
                        'must be package-qualified (tests.) or relative'
                    )
    return errors

def validate(root=ROOT):
    errors=[]
    try:
        load_boundary(root)
        errors.extend(validate_test_imports(root))
        for rel in REQUIRED:
            if not (root/rel).is_file():errors.append('Missing: '+rel)
        successor = (root/'docs/evidence/ai-003/change_boundary.json').is_file()
        expected_head = '20260916_0017' if successor else '20260915_0016'
        if f'CURRENT_REVISION = "{expected_head}"' not in (root/'database.py').read_text():errors.append('Unexpected schema head')
        if successor:
            from scripts.check_ai003_package import validate as validate_ai003
            errors.extend(validate_ai003(root))
        migration=ast.parse((root/'migrations/versions/20260915_0016_resume_analysis.py').read_text())
        created={n.args[0].value for n in ast.walk(migration) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='create_table' and n.args and isinstance(n.args[0],ast.Constant)}
        if created!={'resume_analysis_reports','resume_analysis_decisions','resume_analysis_review_events'}:errors.append('Incorrect additive tables')
        if 'down_revision = "20260914_0015"' not in (root/'migrations/versions/20260915_0016_resume_analysis.py').read_text():errors.append('Wrong migration parent')
        route=(root/'routes/resume_analysis.py').read_text()
        if '.analyze(' in route or '.generate(' in route or 'requests.' in route:errors.append('Reference UI must not call a provider')
        for marker in ('ai_analysis_review_enabled','is_search_admin','request.files','request.is_json','csrf_token','no-store'):
            if marker not in route:errors.append('Missing route safeguard: '+marker)
        config=(root/'config.py').read_text()
        if '_bool(source, "AI_ANALYSIS_REVIEW_ENABLED", False)' not in config:errors.append('Review must default off')
        ref=json.loads((root/'services/ai/analysis_reference_manifest.json').read_text())
        expected={f'prompts/analysis/reference/resume-analysis-{lang}-01.json' for lang in ('ru','en')}
        if set(ref['files'])!=expected or ref['origin']!='reference_not_live_ai':errors.append('Unpinned reference set')
        for rel,sha in ref['files'].items():
            if not matches(root/rel,sha):errors.append('Reference hash mismatch')
        source=(root/'domain/ai.py').read_text()
        if 'REAL_DATA_SUPPORTED = False' not in source:errors.append('Real-data flag changed')
        docs=(root/'docs/AI002_VERIFICATION_STATUS.md').read_text()
        if not all(token in docs for token in ('CI #270', '20260915_0016', 'synthetic/reference-only', 'owner')):errors.append('Accepted AI-002 evidence missing')
        if 'python scripts/check_ai002_package.py' not in (root/'.github/workflows/ci.yml').read_text():errors.append('Missing CI step')
        for rel in ('templates/analysis/index.html','templates/analysis/detail.html'):
            html=(root/rel).read_text()
            if '|safe' in html:errors.append('Unsafe output rendering')
    except (OSError,ValueError,KeyError,TypeError,AttributeError,SyntaxError) as exc:
        errors.append('AI-002 incomplete: '+type(exc).__name__)
    return errors

def main():
    errors=validate();print(json.dumps({'package':'AI-002','scope':'synthetic_only','ok':not errors,'errors':errors},indent=2))
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
