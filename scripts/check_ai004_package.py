#!/usr/bin/env python3
"""Dependency-free AI-004 scope/hash gate, including its exact GitHub baseline."""
from pathlib import Path
import ast
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
SOURCE_COMMIT = 'c683520058cc1f729c79ed49ac5c213811e4c9f3'
SOURCE_TREE = '6458daea23371dadfbbd49d830abcdde44df1293'
CHANGES = {'app.py','database.py','models/__init__.py','operations/backup.py',
           'repositories/privacy.py','services/privacy.py','services/storage.py'}
REQUIRED = {
    'domain/vacancy_match.py','models/vacancy_match.py','repositories/vacancy_match.py',
    'services/vacancy_match.py','services/ai/match_validation.py','services/ai/match_labels.py',
    'services/ai/match_reference_manifest.json','routes/vacancy_match.py','static/vacancy_match.css',
    'migrations/versions/20260916_0018_vacancy_match.py',
    'templates/matching/index.html','templates/matching/detail.html','templates/matching/review_gate.html','templates/matching/error.html',
    'tests/test_ai004_scoring.py','tests/test_ai004_service.py','tests/test_ai004_routes.py','tests/test_ai004_migration.py','tests/test_ai004_package.py',
    'docs/AI004_IMPLEMENTATION.md','docs/AI004_RUNBOOK.md','docs/AI004_VERIFICATION_STATUS.md',
}


def matches(path,digest):
    raw=path.read_bytes()
    return digest in {hashlib.sha256(raw).hexdigest(),hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()}


def load_boundary(root=ROOT):
    data=json.loads((root/'docs/evidence/ai-004/change_boundary.json').read_text())
    base=json.loads((root/'docs/evidence/ai-004/baseline_files_sha256.json').read_text())
    if (data['package']!='AI-004' or data['public_real_data_enabled'] is not False
            or set(data['reviewed_runtime_changes'])!=CHANGES
            or data['source_commit']!=SOURCE_COMMIT or data['source_tree']!=SOURCE_TREE
            or base['source_commit']!=SOURCE_COMMIT or base['source_tree']!=SOURCE_TREE):
        raise ValueError('Invalid AI-004 scope or source')
    parent=json.loads((root/'docs/evidence/ai-003/change_boundary.json').read_text())['reviewed_runtime_changes']
    successor = {}
    if (root/'docs/evidence/job-001/change_boundary.json').is_file():
        from scripts.check_job001_package import load_boundary as load_job001_boundary
        successor = load_job001_boundary(root)
    effective = {}
    for rel,row in data['reviewed_runtime_changes'].items():
        if row['previous_sha256']!=base['files'].get(rel):
            raise ValueError('AI-004 baseline mismatch')
        if rel in parent and row['previous_sha256']!=parent[rel]['current_sha256']:
            raise ValueError('AI-004 parent mismatch')
        current = successor.get(rel, row)['current_sha256']
        if not matches(root/rel,current):
            raise ValueError('AI-004 runtime checksum mismatch')
        effective[rel] = {**row, 'current_sha256': current}
    return {**effective, **successor}


def validate_closure(root=ROOT):
    """Check explicit closure provenance, not old pending words in an appendix.

    This is a consistency check for recorded evidence, not a claim that running
    a local checker independently re-executes CI or the owner's browser tests.
    """
    errors = []
    try:
        status = (root / 'docs/AI004_VERIFICATION_STATUS.md').read_text()
        current = next((line for line in status.splitlines() if line.startswith('| Status |')), '')
        if 'COMPLETE' not in current or 'synthetic/reference-only' not in current:
            errors.append('AI-004 current closure status is missing or overbroad')
        data = json.loads((root / 'docs/evidence/ai-004/acceptance.json').read_text())
        code = data['accepted_code']
        if (data['package'] != 'AI-004' or data['status'] != 'COMPLETE'
                or data['scope'] != 'synthetic/reference-only'
                or code['commit'] != 'd5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4'
                or code['tree'] != '53d86b0ff72f5090f214c20979df493e6f1f0ee3'):
            errors.append('AI-004 accepted application provenance is inconsistent')
        ci = data['github']['main_ci']
        if (ci['run_id'] != 35151012823 or ci['run_number'] != 281
                or ci['conclusion'] != 'success'
                or ci['ai004_tests']['passed'] != 71 or ci['ai004_tests']['skipped'] != 0
                or ci['final_pytest']['passed'] != 804 or ci['final_pytest']['skipped'] != 0):
            errors.append('AI-004 external CI evidence is inconsistent')
        owner = data['owner_acceptance']
        if (owner['schema'] != '20260916_0018' or owner['migrations_ok'] is not True
                or owner['generation_available'] is not False or owner['mode'] != 'manual'
                or owner['reason'] != 'runtime_not_activated'):
            errors.append('AI-004 closure must preserve the manual runtime boundary')
        if data['manual_two_account_isolation']['status'] != 'NOT RUN':
            errors.append('Manual two-account isolation must not be invented')
        if ('NOT EVIDENCED' not in data['real_database_backup']
                or not data['real_database_restore'].startswith('NOT RUN')):
            errors.append('Real recovery evidence must not be invented')
        if (data['next_package']['implementation_started'] is not False
                or data['next_package']['sequence_change_approved'] is not False
                or data['next_package']['unmet_dependency'] != 'JOB-001'):
            errors.append('Next-package preparation must preserve the unresolved dependency')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        errors.append('Missing or malformed AI-004 closure evidence')
    return errors


def validate(root=ROOT):
    errors=[]
    try:
        load_boundary(root)
        for rel in REQUIRED:
            if not (root/rel).is_file():errors.append('Missing: '+rel)
        has_job001 = (root/'docs/evidence/job-001/change_boundary.json').is_file()
        expected_head = '20261001_0022' if (root/'docs/evidence/job-002/change_boundary.json').is_file() else '20260922_0021' if (root/'docs/evidence/legal-001/change_boundary.json').is_file() else '20260917_0020' if (root/'docs/evidence/ai-005/change_boundary.json').is_file() else '20260917_0019' if has_job001 else '20260916_0018'
        if f'CURRENT_REVISION = "{expected_head}"' not in (root/'database.py').read_text():
            errors.append('Unexpected schema head')
        if has_job001:
            from scripts.check_job001_package import validate as validate_job001
            errors.extend(validate_job001(root))
        migration=(root/'migrations/versions/20260916_0018_vacancy_match.py').read_text()
        created={n.args[0].value for n in ast.walk(ast.parse(migration)) if isinstance(n,ast.Call)
                 and isinstance(n.func,ast.Attribute) and n.func.attr=='create_table' and n.args and isinstance(n.args[0],ast.Constant)}
        if created!={'vacancy_match_series','vacancy_match_reports'} or "down_revision = '20260916_0017'" not in migration:
            errors.append('Incorrect additive migration')
        route=(root/'routes/vacancy_match.py').read_text()
        if any(x in route for x in ('.analyze(','.generate(', 'csrf.exempt', 'AI_ENABLED')):
            errors.append('Private review must never dispatch a provider or bypass CSRF')
        for marker in ('is_search_admin','_REVIEW_SESSION_KEY','request.files','request.is_json',
                       'getlist','csrf_token','no-store','noindex, nofollow','g.current_user.id'):
            if marker not in route:errors.append('Missing route guard: '+marker)
        if 'REAL_DATA_SUPPORTED = False' not in (root/'domain/ai.py').read_text():
            errors.append('Real data was enabled')
        base=json.loads((root/'docs/evidence/ai-004/baseline_files_sha256.json').read_text())['files']
        # No successor permission is granted for model prompts, golden tests,
        # dependencies, runtime switches, pricing or provider policy.
        for rel,sha in base.items():
            if rel.startswith(('evals/','prompts/','schemas/','docs/policies/','services/ai/')) or rel in {'requirements.txt','requirements-dev.txt','domain/ai.py','config.py','render.yaml'}:
                if not matches(root/rel,sha):errors.append('Protected source changed: '+rel)
        manifest=json.loads((root/'services/ai/match_reference_manifest.json').read_text())
        wanted={f'prompts/matching/reference/vacancy-match-{lang}-01.json' for lang in ('ru','en')}
        if set(manifest['files'])!=wanted or manifest['origin']!='reference_not_live_ai':
            errors.append('Unpinned matching reference')
        for rel,sha in manifest['files'].items():
            if not matches(root/rel,sha):errors.append('Reference checksum mismatch: '+rel)
        for path in (root/'templates/matching').glob('*.html'):
            code=path.read_text()
            if any(x in code for x in ('|safe','<script','<textarea','type="file"','onclick=')):
                errors.append('Unsafe or real-data template: '+path.name)
        workflow=(root/'.github/workflows/ci.yml').read_text()
        if 'python scripts/check_ai004_package.py' not in workflow or 'test_ai004_routes.py' not in workflow:
            errors.append('Missing AI-004 CI gate')
        errors.extend(validate_closure(root))
        for path in (root/'tests').glob('test_ai004*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.ImportFrom) and node.level==0 and (node.module or '').startswith('test_'):
                    errors.append('Bare sibling test import: '+path.name)
    except (OSError,ValueError,KeyError,TypeError,AttributeError,SyntaxError):
        errors.append('Missing or invalid AI-004 boundary')
    return errors


def main():
    errors=validate()
    print(json.dumps({'package':'AI-004','scope':'synthetic/reference-only','ok':not errors,'errors':errors},indent=2))
    return int(bool(errors))

if __name__=='__main__':
    raise SystemExit(main())
