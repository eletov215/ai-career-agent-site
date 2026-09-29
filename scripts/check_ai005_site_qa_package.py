#!/usr/bin/env python3
"""SITE QA successor proof; historical runtime and guards remain byte-preserved."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = 'b828596c893d59a544f9678d7b45ab6ed7f44230'
TREE = '05fc57dd0294cd5814637cc6e61e864f2bba9d2d'
PROTECTED = {
    'app.py':'a75c6e858a9ee03a181f79bf7c3d7e3343d0c179',
    'database.py':'9c24c8deabe2835ba0d66c871be410163ddb24f6',
    'domain/ai.py':'7ce1cdec24c44ae147deaf4bce677fdc04b93eb5',
    'services/legal_policy.py':'9786d82b5fb3317c24845b6e44555de9cc3a21bd',
    'services/ai/provider.py':'63669e5ddeca995a852a76b61744c0084332d7a8',
    'services/ai/settings.py':'aa949b018d97b8d68dce5a12fe6dfc9d9c6a4545',
    'services/ai/letter_admission.py':'38a2d1fd9ea27fb22995e4dfef8e06de75e3dcfd',
    'services/ai/letter_runtime.py':'c5a6dea1356153c9f5cfdd5b7452db84c773516e',
    'services/ai/letter_contract.py':'d96160fcd5c9b3de4c52563df009916e685a0d20',
    'services/cover_letter_ai.py':'b26cd3cb6470d328721bdcd2ca90917db92fb0aa',
    'services/cover_letters.py':'1fa5ff4eea762d8d6132ea8f9b88491576884a1d',
    'repositories/ai.py':'aafdd2adf62f4a77930d159bf882b774fbecab79',
    'repositories/cover_letters.py':'182719d138f25d092b3a8fa43125c0c4757c8e28',
    'routes/cover_letters.py':'8a8264da091fbbd090e7aec634d5bf8b427d0990',
    'scripts/legal001_boundary.py':'d7084289514223c6871f9217cfa7a011009238dc',
    'scripts/check_ai005_package.py':'7026ceb369a6cae102972938b8947a14a875f86a',
    'scripts/check_ai005_r2_package.py':'372672bfd7bf1fd3493a3f0cf7970d27595e3ddb',
}
INTEGRATION = ('    # Independent synthetic QA namespace; ordinary source-health routes stay read-only.\n'
    '    from routes.letter_site_qa import create_letter_site_qa_blueprint\n'
    '    bp.register_blueprint(create_letter_site_qa_blueprint(settings, storage))\n\n')
RUNTIME = {'services/letter_site_qa.py', 'repositories/letter_site_qa.py', 'routes/letter_site_qa.py',
           'templates/letters/site_qa.html', 'static/letter_site_qa.css'}
NO_LOGGING_EVIDENCE = 'docs/evidence/ai-005-site-qa-no-logging/change_boundary.json'
NO_LOGGING_FILES = {'services/letter_site_qa.py', 'services/ai/site_qa_gate.py'}

PROVIDER_INTEGRATION = '        if (root / "docs/evidence/ai-005-site-qa/change_boundary.json").is_file():\n            from scripts.check_ai005_site_qa_package import successor_hashes as site_qa_successor\n            successor = {\n                **successor,\n                **{relative: {"current_sha256": sha} for relative, sha in site_qa_successor(root).items()},\n            }\n'
PROVIDER_BASE_BLOB = '80deee17f57d54f26a965c2a6b175bd34f549aca'


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def validate(root=ROOT):
    errors = []
    try:
        protected = dict(PROTECTED)
        live_qa = root/'docs/evidence/ai-005-live-qa-001/change_boundary.json'
        if live_qa.is_file():
            from scripts.check_ai005_live_qa_boundary import successor_hashes as live_qa_hashes
            protected.update(live_qa_hashes(root))
        evidence = json.loads((root/'docs/evidence/ai-005-site-qa/change_boundary.json').read_text())
        if (evidence['source_commit'] != BASE or evidence['source_tree'] != TREE
                or evidence['real_data_enabled'] is not False or evidence['legal_state'] != 'DRAFT'
                or evidence['paid_provider_calls'] != 0 or evidence['schema'] != '20260922_0021'
                or set(evidence['runtime_git_blobs']) != RUNTIME):
            errors.append('Invalid SITE QA scope')
        for path, sha in protected.items():
            raw = (root/path).read_bytes()
            if sha not in {blob(raw), blob(raw.replace(b'\r\n', b'\n')),
                           hashlib.sha256(raw).hexdigest(),
                           hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()}:
                errors.append('Protected predecessor changed: ' + path)
        route = (root/'routes/admin_sources.py').read_text()
        if route.count(INTEGRATION) != 1 or blob(route.replace(INTEGRATION, '').encode()) != 'f4f268c16a495abc6a4f2111971788bb106a6115':
            errors.append('Unreviewed admin integration change')
        provider_guard = (root/'scripts/check_ai_provider_package.py').read_text()
        if (provider_guard.count(PROVIDER_INTEGRATION) != 1
                or blob(provider_guard.replace(PROVIDER_INTEGRATION, '').encode()) != PROVIDER_BASE_BLOB):
            errors.append('Unreviewed provider guard change')
        successor = json.loads((root/NO_LOGGING_EVIDENCE).read_text())
        if (successor.get('package') != 'AI-005-SITE-QA-NO-LOGGING-WAIT'
                or successor.get('source_commit') != 'cd526df75ca13cfed310114be1d96c0551ecb06b'
                or successor.get('real_data_enabled') is not False
                or successor.get('legal_state') != 'DRAFT'
                or successor.get('paid_provider_calls') != 0
                or set(successor.get('runtime_git_blobs', {})) != NO_LOGGING_FILES
                or successor.get('superseded_git_blobs') != {
                    'services/letter_site_qa.py': evidence['runtime_git_blobs']['services/letter_site_qa.py']}):
            errors.append('Invalid SITE QA no-logging successor scope')
        runtime_hashes = {**evidence['runtime_git_blobs'], **successor.get('runtime_git_blobs', {})}
        for path, sha in runtime_hashes.items():
            raw = (root/path).read_bytes()
            if sha not in {blob(raw), blob(raw.replace(b'\r\n',b'\n'))}:
                errors.append('SITE QA runtime hash mismatch: ' + path)
            if path.endswith('.py'):
                tree = ast.parse(raw)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'exempt':
                        errors.append('Unexpected security exemption')
                    if isinstance(node, ast.ImportFrom) and (node.module or '').startswith('tests'):
                        errors.append('Test code imported by production')
        service = (root/'services/letter_site_qa.py').read_text()
        for marker in ('SyntheticLetterAdmission', 'LetterRuntime', "ticket['issued'] = record['created_at']", 'site-qa-one-dispatch-v1', 'self.qa.authorize'):
            if marker not in service:
                errors.append('Missing fixed-intention/admission boundary: ' + marker)
        storage = (root/'repositories/letter_site_qa.py').read_text()
        if any(marker in service + storage for marker in ('update_policy(', 'os.environ')):
            errors.append('SITE QA must not activate policy or accept environment-supplied sources')
        if 'from models' in service or 'from sqlalchemy' in service or 'session.execute' in service:
            errors.append('SITE QA service must delegate database access to repository')
        gate = (root/'services/ai/site_qa_gate.py').read_text()
        for marker in ('reason = self.settings.gate(now)', 'reason == "no_logging_wait"',
                       'else reason', '@dataclass(frozen=True, slots=True)'):
            if marker not in gate:
                errors.append('Invalid SITE-QA-only no-logging gate: ' + marker)
        if any(marker in gate for marker in ('os.environ', 'request.', 'REAL_DATA_SUPPORTED')):
            errors.append('SITE QA gate must not be client/environment selectable or activate real data')
        template = (root/'templates/letters/site_qa.html').read_text()
        if '|safe' in template or 'csrf_token()' not in template:
            errors.append('Unsafe SITE QA template')
        preview = template.split("{% elif view == 'preview' %}", 1)[1].split("{% elif view == 'version' %}", 1)[0]
        if 'type="checkbox"' in preview or 'name="confirm"' in preview:
            errors.append('Per-call confirmation checkbox reintroduced')
        workflow = (root/'.github/workflows/ai005-site-qa.yml').read_text()
        if 'APP_ENV: test' not in workflow or 'test_ai005_site_qa_postgresql.py' not in workflow or 'secrets.' in workflow:
            errors.append('Missing isolated no-paid-call CI')
    except (OSError, ValueError, KeyError, TypeError, IndexError, SyntaxError):
        errors.append('Missing or invalid SITE QA evidence')
    return errors


def successor_hashes(root=ROOT):
    """Only the reviewed admin registration can supersede the older provider gate."""
    errors = validate(root)
    if errors:
        raise ValueError('Invalid SITE QA successor evidence')
    return {'routes/admin_sources.py': hashlib.sha256((root/'routes/admin_sources.py').read_bytes()).hexdigest()}


if __name__ == '__main__':
    errors = validate()
    print(json.dumps({'package':'AI-005-SITE-QA', 'ok':not errors, 'errors':errors,
        'paid_provider_calls':0, 'real_data_enabled':False, 'ci':'NOT_ATTESTED_BY_STATIC_CHECK'}, indent=2))
    raise SystemExit(bool(errors))
