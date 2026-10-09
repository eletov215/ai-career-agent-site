#!/usr/bin/env python3
"""JOB-001 source/closure guard. Checks recorded evidence, not remote CI live."""
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
    successor = {}
    if (root/'docs/evidence/ai-005/change_boundary.json').is_file():
        from scripts.check_ai005_package import load_boundary as load_ai005
        successor = load_ai005(root)
    effective = {}
    for rel, row in data['reviewed_runtime_changes'].items():
        if row['previous_sha256'] != base['files'].get(rel):
            raise ValueError('JOB-001 baseline mismatch')
        if rel in parent and row['previous_sha256'] != parent[rel]['current_sha256']:
            raise ValueError('JOB-001 parent mismatch')
        if rel in successor and successor[rel]['previous_sha256'] != row['current_sha256']:
            raise ValueError('AI-005 predecessor mismatch')
        current = successor.get(rel, row)['current_sha256']
        if not matches(root/rel, current):
            raise ValueError('JOB-001 runtime mismatch')
        effective[rel] = {**row, 'current_sha256': current}
    for rel, sha in data['new_runtime_sha256'].items():
        if rel in successor and successor[rel]['previous_sha256'] != sha:
            raise ValueError('AI-005 new predecessor mismatch')
        current = successor.get(rel, {}).get('current_sha256', sha)
        if not matches(root/rel, current):
            raise ValueError('JOB-001 new runtime mismatch')
    return {**effective, **successor}


ACCEPTED_COMMIT = 'c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c'
ACCEPTED_TREE = '6bb34aba4c05213a3d68f784e9d9b385c6d577d3'


def validate_closure(root=ROOT):
    """Require the recorded acceptance without turning unrun cases into passes."""
    errors = []
    try:
        data = json.loads((root/'docs/evidence/job-001/acceptance.json').read_text())
        ci = data['github']
        if (data['package'] != 'JOB-001' or data['status'] != 'COMPLETE'
                or data['accepted_release'] != 'r1.1 REBUILT'
                or data['closure_release'] != '1.6.1'
                or data['accepted_code'] != {'commit': ACCEPTED_COMMIT, 'tree': ACCEPTED_TREE, 'files': 608}):
            errors.append('JOB-001 accepted source is inconsistent')
        if (ci['run_id'] != 35219447896 or ci['run_number'] != 283
                or ci['head_sha'] != ACCEPTED_COMMIT or ci['branch'] != 'main'
                or ci['status'] != 'completed' or ci['conclusion'] != 'success'
                or ci['python_job_id'] != 105195697162
                or ci['job001_step_conclusion'] != 'success' or ci['paid_jobs'] != 'skipped'
                or ci['exact_test_counts'] is not None):
            errors.append('JOB-001 recorded CI is inconsistent')
        owner = data['owner_acceptance']
        if (owner['schema'] != '20260917_0019' or owner['migrations_ok'] is not True
                or owner['generation_available'] is not False or owner['mode'] != 'manual'
                or owner['reason'] != 'runtime_not_activated'
                or owner['final_status'] != 'PASS_OWNER_REPORTED'
                or owner['assistant_ran_production_browser'] is not False):
            errors.append('JOB-001 owner evidence or runtime boundary is inconsistent')
        required = {'readiness','manual_ai','save_and_snapshot','refresh_relogin','notes','stale_note',
                    'duplicate_save','filter','export','stale_delete','confirmed_delete','logout_access',
                    'regression','final_gate_logs'}
        if set(owner['cases']) != required or not all(isinstance(v,str) and v.strip() for v in owner['cases'].values()):
            errors.append('JOB-001 owner case matrix is incomplete')
        if (data['manual_two_account_isolation']['status'] != 'NOT RUN'
                or data['manual_restart']['status'] != 'NOT RUN'
                or data['manual_legacy_import']['status'] != 'NOT SEPARATELY CONFIRMED'
                or data['manual_second_device']['status'] != 'NOT SEPARATELY CONFIRMED'):
            errors.append('JOB-001 optional manual evidence must not be invented')
        if (not data['real_database_backup'].startswith('NOT EVIDENCED')
                or not data['real_database_restore'].startswith('NOT RUN')):
            errors.append('JOB-001 real recovery evidence must not be invented')
        for key in ('application_changed_by_closure','new_migration','public_ai_activated','new_paid_provider_calls','closure_published'):
            if data[key] is not False:
                errors.append('JOB-001 closure boundary changed: '+key)
        if (data['next_package']['id'] != 'AI-005'
                or data['next_package']['job001_dependency_satisfied'] is not True
                or data['next_package']['implementation_started'] is not False
                or data['next_package']['full_live_activation_ready'] is not False):
            errors.append('JOB-001 next-package gate is inconsistent')
        status = (root/'docs/JOB001_VERIFICATION_STATUS.md').read_text()
        if '| Status |' not in status or '/ COMPLETE in the server-saved vacancy scope' not in status or '1.2 FINAL' not in status:
            errors.append('JOB-001 final status document is inconsistent')
        for rel in ('docs/PLAN_CURRENT.md','docs/PROJECT_PASSPORT.md'):
            doc = (root/rel).read_text()
            head = doc.split('<!-- ACA-CANONICAL-STATUS:START -->',1)[1].split('<!-- ACA-CANONICAL-STATUS:END -->',1)[0]
            if not all(x in head for x in ('JOB-001','COMPLETE',ACCEPTED_COMMIT,'1.6.1','2.76','20260917_0019')):
                errors.append('JOB-001 canonical status is inconsistent: '+rel)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError):
        errors.append('Missing or malformed JOB-001 acceptance evidence')
    return errors


def validate(root=ROOT):
    errors = []
    try:
        load_boundary(root)
        for rel in REQUIRED:
            if not (root/rel).is_file():
                errors.append('Missing: '+rel)
        expected_head = '20261002_0023' if (root/'docs/evidence/job-003/change_boundary.json').is_file() else '20261001_0022' if (root/'docs/evidence/job-002/change_boundary.json').is_file() else '20260922_0021' if (root/'docs/evidence/legal-001/change_boundary.json').is_file() else '20260917_0020' if (root/'docs/evidence/ai-005/change_boundary.json').is_file() else '20260917_0019'
        from scripts.ai004_m04b_successor import expected_schema_head
        expected_head = expected_schema_head(root, expected_head)
        if f'CURRENT_REVISION = "{expected_head}"' not in (root/'database.py').read_text():
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
        errors.extend(validate_closure(root))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError):
        errors.append('JOB-001 evidence incomplete or invalid')
    return errors


if __name__ == '__main__':
    errors=validate()
    print(json.dumps({'package':'JOB-001','release':'r1.1 REBUILT / closure1.6.1','external_ci':'recorded_success_for_accepted_application',
                      'ok':not errors,'errors':errors},indent=2))
    raise SystemExit(bool(errors))
