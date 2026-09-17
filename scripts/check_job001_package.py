#!/usr/bin/env python3
"""Dependency-free JOB-001 additive hash/scope gate. Does not attest external CI."""
from pathlib import Path
import ast
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE_COMMIT = 'd5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4'
SOURCE_TREE = '53d86b0ff72f5090f214c20979df493e6f1f0ee3'
CHANGES = {'app.py', 'database.py', 'models/__init__.py', 'operations/backup.py',
           'repositories/privacy.py', 'services/privacy.py', 'services/storage.py',
           'services/search_aggregation.py', 'templates/base.html', 'templates/vacancies_unified.html'}
NEW_RUNTIME = {'domain/saved_vacancy.py', 'models/saved_vacancy.py', 'repositories/saved_vacancies.py',
               'services/saved_vacancies.py', 'services/saved_vacancy_snapshot.py',
               'services/saved_vacancy_labels.py', 'routes/saved_vacancies.py',
               'migrations/versions/20260917_0019_saved_vacancies.py',
               'static/saved_vacancies.css', 'static/saved_vacancies.js',
               'templates/saved_vacancies/index.html','templates/saved_vacancies/detail.html',
               'templates/saved_vacancies/error.html','templates/saved_vacancies/conflict.html'}
EVIDENCE = {'docs/evidence/job-001/change_boundary.json', 'docs/evidence/job-001/baseline_files_sha256.json'}
REQUIRED = NEW_RUNTIME | {'docs/JOB001_IMPLEMENTATION.md','docs/JOB001_RUNBOOK.md','docs/JOB001_VERIFICATION_STATUS.md',
                          'tests/test_job001_service.py','tests/test_job001_routes.py',
                          'tests/test_job001_migration.py','tests/test_job001_package.py'}


def matches(path, expected):
    raw = path.read_bytes()
    return expected in {hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()}


def load_boundary(root=ROOT):
    data = json.loads((root/'docs/evidence/job-001/change_boundary.json').read_text())
    base = json.loads((root/'docs/evidence/job-001/baseline_files_sha256.json').read_text())
    if (data['package'] != 'JOB-001' or data['public_real_data_enabled'] is not False
            or data['source_commit'] != SOURCE_COMMIT or data['source_tree'] != SOURCE_TREE
            or base['source_commit'] != SOURCE_COMMIT or base['source_tree'] != SOURCE_TREE
            or set(data['reviewed_runtime_changes']) != CHANGES
            or set(data['new_runtime_sha256']) != NEW_RUNTIME):
        raise ValueError('Invalid JOB-001 boundary')
    parent = json.loads((root/'docs/evidence/ai-004/change_boundary.json').read_text())['reviewed_runtime_changes']
    for rel, row in data['reviewed_runtime_changes'].items():
        if row['previous_sha256'] != base['files'].get(rel):
            raise ValueError('JOB-001 baseline mismatch')
        if rel in parent and row['previous_sha256'] != parent[rel]['current_sha256']:
            raise ValueError('JOB-001 parent mismatch')
        if not matches(root/rel, row['current_sha256']):
            raise ValueError('JOB-001 runtime mismatch')
    for rel, sha in data['new_runtime_sha256'].items():
        if not matches(root/rel, sha):
            raise ValueError('JOB-001 new runtime mismatch')
    return data['reviewed_runtime_changes']


def validate(root=ROOT):
    errors = []
    try:
        load_boundary(root)
        for rel in REQUIRED:
            if not (root/rel).is_file():
                errors.append('Missing: '+rel)
        if 'CURRENT_REVISION = "20260917_0019"' not in (root/'database.py').read_text():
            errors.append('Expected schema 0019')
        source = (root/'migrations/versions/20260917_0019_saved_vacancies.py').read_text()
        names = {node.args[0].value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == 'create_table'
                 and node.args and isinstance(node.args[0], ast.Constant)}
        if names != {'saved_vacancies','saved_vacancy_sources'} or "down_revision = '20260916_0018'" not in source:
            errors.append('Invalid additive migration')
        base = json.loads((root/'docs/evidence/job-001/baseline_files_sha256.json').read_text())['files']
        for rel, sha in base.items():
            if rel.startswith(('prompts/','schemas/','evals/','services/ai/','docs/policies/')) or rel in {
                    'config.py','render.yaml','requirements.txt','requirements-dev.txt','domain/ai.py'}:
                if not matches(root/rel, sha):errors.append('Protected source changed: '+rel)
        if 'REAL_DATA_SUPPORTED = False' not in (root/'domain/ai.py').read_text():
            errors.append('Public AI must remain off')
        route = (root/'routes/saved_vacancies.py').read_text()
        for marker in ('g.current_user.id','email_verified_at','csrf_token','expected_revision','confirm','no-store','request.files'):
            if marker not in route:errors.append('Missing route control: '+marker)
        if 'csrf.exempt' in route:errors.append('CSRF bypass is forbidden')
        for rel in ('routes/saved_vacancies.py','repositories/saved_vacancies.py','services/saved_vacancies.py'):
            for node in ast.walk(ast.parse((root/rel).read_text())):
                modules = [node.module or ''] if isinstance(node, ast.ImportFrom) else [n.name for n in node.names] if isinstance(node, ast.Import) else []
                if any(m.startswith(('requests','httpx','urllib.request','services.ai')) for m in modules):
                    errors.append('Network or AI import in '+rel)
        for path in (root/'templates/saved_vacancies').glob('*.html'):
            if '|safe' in path.read_text():errors.append('Unescaped template')
        workflow=(root/'.github/workflows/ci.yml').read_text()
        if 'python scripts/check_job001_package.py' not in workflow or 'test_job001_routes.py' not in workflow:
            errors.append('Missing ordinary JOB-001 CI step')
        status=(root/'docs/JOB001_VERIFICATION_STATUS.md').read_text()
        if 'NEEDS_VERIFICATION' not in status or 'REBUILT' not in status:
            errors.append('Rebuilt release must not invent external acceptance')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError):
        errors.append('JOB-001 evidence incomplete or invalid')
    return errors


if __name__ == '__main__':
    errors=validate()
    print(json.dumps({'package':'JOB-001','release':'r1.1 REBUILT','external_ci':'not_run',
                      'ok':not errors,'errors':errors},indent=2))
    raise SystemExit(bool(errors))
