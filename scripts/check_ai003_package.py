#!/usr/bin/env python3
"""Dependency-free AI-003 successor checks. Never imports application/ORM code."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CHANGES = {
    'app.py', 'config.py', 'database.py', 'compose.yaml', 'render.yaml', 'infra/vps/.env.example',
    'models/__init__.py', 'operations/backup.py', 'repositories/privacy.py', 'routes/resume_drafts.py',
    'services/privacy.py', 'services/storage.py', 'templates/resume_builder.html',
}
REQUIRED = {
    'domain/resume_interview.py', 'models/resume_interview.py', 'repositories/resume_interview.py',
    'services/resume_interview.py', 'services/ai/interview_reference.py', 'services/ai/interview_labels.py',
    'services/ai/interview_reference_manifest.json', 'routes/resume_interview.py',
    'migrations/versions/20260916_0017_resume_interview.py',
    'templates/interview/index.html', 'templates/interview/detail.html', 'templates/interview/error.html',
    'templates/interview/review_gate.html',
    'static/resume_interview.css', 'tests/test_ai003_service.py', 'tests/test_ai003_routes.py',
    'tests/test_ai003_migration.py', 'tests/test_ai003_package.py',
    'docs/AI003_IMPLEMENTATION.md', 'docs/AI003_RUNBOOK.md', 'docs/AI003_VERIFICATION_STATUS.md',
}


def matches(path, expected):
    raw = path.read_bytes()
    return expected in {hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()}


def load_boundary(root=ROOT):
    data = json.loads((root/'docs/evidence/ai-003/change_boundary.json').read_text())
    baseline = json.loads((root/'docs/evidence/ai-003/baseline_files_sha256.json').read_text())
    if data['package'] != 'AI-003' or data['public_real_data_enabled'] is not False or set(data['reviewed_runtime_changes']) != CHANGES:
        raise ValueError('Invalid AI-003 scope')
    if data['source_sha256'] != baseline['source_sha256'] or data['source_commit'] != baseline['source_commit']:
        raise ValueError('AI-003 source mismatch')
    older = json.loads((root/'docs/evidence/ai-001/change_boundary.json').read_text())['reviewed_runtime_changes']
    parent = json.loads((root/'docs/evidence/ai-002/change_boundary.json').read_text())['reviewed_runtime_changes']
    successor = {}
    if (root/'docs/evidence/ai-004/change_boundary.json').is_file():
        from scripts.check_ai004_package import load_boundary as load_ai004_boundary
        successor = load_ai004_boundary(root)
    effective = {}
    for rel, item in data['reviewed_runtime_changes'].items():
        if item['previous_sha256'] != baseline['files'].get(rel):
            raise ValueError('AI-003 baseline checksum mismatch')
        expected = parent.get(rel, older.get(rel, {})).get('current_sha256')
        if expected and item['previous_sha256'] != expected:
            raise ValueError('AI-003 parent checksum mismatch')
        current = successor.get(rel, item)['current_sha256']
        if not matches(root/rel, current):
            raise ValueError('AI-003 runtime checksum mismatch')
        effective[rel] = {**item, 'current_sha256': current}
    return {**effective, **successor}


def validate(root=ROOT):
    errors = []
    try:
        load_boundary(root)
        for rel in REQUIRED:
            if not (root/rel).is_file():
                errors.append('Missing: '+rel)
        successor = (root/'docs/evidence/ai-004/change_boundary.json').is_file()
        expected_head = '20260917_0019' if (root/'docs/evidence/job-001/change_boundary.json').is_file() else '20260916_0018' if successor else '20260916_0017'
        if f'CURRENT_REVISION = "{expected_head}"' not in (root/'database.py').read_text():
            errors.append('Unexpected schema head')
        if successor:
            from scripts.check_ai004_package import validate as validate_ai004
            errors.extend(validate_ai004(root))
        source = (root/'migrations/versions/20260916_0017_resume_interview.py').read_text()
        migration = ast.parse(source)
        created = {n.args[0].value for n in ast.walk(migration) if isinstance(n, ast.Call) and
                   isinstance(n.func, ast.Attribute) and n.func.attr == 'create_table' and n.args and isinstance(n.args[0], ast.Constant)}
        if created != {'resume_interview_sessions', 'resume_interview_events'} or "down_revision = '20260915_0016'" not in source:
            errors.append('Incorrect additive migration')
        render = (root/'render.yaml').read_text()
        if '- key: AI_INTERVIEW_REVIEW_ENABLED\n        sync: false' not in render or '- key: AI_INTERVIEW_REVIEW_ENABLED\n        value:' in render:
            errors.append('Render interview review flag must be dashboard-controlled')
        config = (root/'config.py').read_text()
        if '_bool(source, "AI_INTERVIEW_REVIEW_ENABLED", False)' not in config:
            errors.append('Private review must default off')
        for rel in ('routes/resume_interview.py', 'services/resume_interview.py', 'services/ai/interview_reference.py'):
            code = (root/rel).read_text()
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    if module.startswith(('requests', 'httpx', 'urllib', 'services.ai.provider', 'services.ai.service')):
                        errors.append('Reference flow must not import a provider: '+rel)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {'generate', 'analyze'}:
                    errors.append('Reference flow must not dispatch a provider: '+rel)
        route = (root/'routes/resume_interview.py').read_text()
        for guard in ('is_search_admin', 'ai_interview_review_enabled', '_REVIEW_SESSION_KEY', 'review_gate',
                      'request.files', 'csrf_token', 'no-store', 'object_pairs_hook'):
            if guard not in route:
                errors.append('Missing private route control: '+guard)
        manifest = json.loads((root/'services/ai/interview_reference_manifest.json').read_text())
        wanted = {'schemas/interview/reference_v1.schema.json'} | {
            f'prompts/interview/reference/resume-interview-{language}-01.json' for language in ('ru', 'en')}
        if set(manifest['files']) != wanted:
            errors.append('Reference fixture scope changed')
        for rel, digest in manifest['files'].items():
            if not matches(root/rel, digest):
                errors.append('Reference checksum changed: '+rel)
        for rel in ('templates/interview/index.html', 'templates/interview/detail.html'):
            html = (root/rel).read_text()
            if '|safe' in html or '<textarea' in html or 'type="file"' in html or 'csrf_token' not in html:
                errors.append('Reference-only template boundary invalid: '+rel)
        tests = root/'tests'
        for path in tests.glob('test_ai003*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or '').startswith('test_'):
                    errors.append('Unqualified sibling test import: '+path.name)
        if 'python scripts/check_ai003_package.py' not in (root/'.github/workflows/ci.yml').read_text():
            errors.append('Missing ordinary CI gate')
        status = (root/'docs/AI003_VERIFICATION_STATUS.md').read_text()
        accepted = all(token in status for token in ('PASS in synthetic/reference-only scope', '20260916_0017', 'generation_available=false', 'CI #276'))
        pending = all(token in status for token in ('NEEDS_VERIFICATION', 'PENDING', 'NOT RUN', '20260916_0017'))
        if not (accepted or pending):
            errors.append('AI-003 verification status is incomplete or overclaims evidence')
        if 'REAL_DATA_SUPPORTED = False' not in (root/'domain/ai.py').read_text():
            errors.append('Public real-data flag changed')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError):
        errors.append('AI-003 evidence or contract incomplete')
    return errors


def main():
    errors = validate()
    print(json.dumps({'package': 'AI-003', 'scope': 'synthetic/reference-only', 'ok': not errors, 'errors': errors}, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
