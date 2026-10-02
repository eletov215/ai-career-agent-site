#!/usr/bin/env python3
"""AI-005 explicit successor scope; never equates local tests with live acceptance."""
from pathlib import Path
import ast
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
BASE_COMMIT='c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c'
BASE_TREE='6bb34aba4c05213a3d68f784e9d9b385c6d577d3'
CHANGES={'app.py','database.py','models/__init__.py','services/storage.py','services/privacy.py',
         'repositories/privacy.py','operations/backup.py','repositories/saved_vacancies.py',
         'routes/saved_vacancies.py','services/saved_vacancy_labels.py','templates/saved_vacancies/detail.html'}
NEW_RUNTIME={'domain/cover_letter.py','models/cover_letter.py','repositories/cover_letters.py',
    'services/cover_letters.py','services/cover_letter_source.py','services/cover_letter_generation.py',
    'services/cover_letter_labels.py','routes/cover_letters.py','static/cover_letters.css',
    'migrations/versions/20260917_0020_cover_letters.py'} | {
    'templates/letters/'+name+'.html' for name in ('_options','_source','index','detail','version','conflict','compare','error')}
EVIDENCE={'docs/evidence/ai-005/change_boundary.json','docs/evidence/ai-005/baseline_files_sha256.json'}


def matches(path,sha):
    raw=path.read_bytes()
    return sha in {hashlib.sha256(raw).hexdigest(),hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()}


def load_boundary(root=ROOT):
    data=json.loads((root/'docs/evidence/ai-005/change_boundary.json').read_text())
    base=json.loads((root/'docs/evidence/ai-005/baseline_files_sha256.json').read_text())
    if (data['package']!='AI-005' or data['source_commit']!=BASE_COMMIT or data['source_tree']!=BASE_TREE
            or data['public_real_data_enabled'] is not False or set(data['reviewed_runtime_changes'])!=CHANGES
            or set(data['new_runtime_sha256'])!=NEW_RUNTIME or base['source_commit']!=BASE_COMMIT or base['source_tree']!=BASE_TREE):
        raise ValueError('Invalid AI-005 scope')
    successor={}
    if (root/'docs/evidence/ai-005-r2/change_boundary.json').is_file():
        from scripts.check_ai005_r2_package import load_boundary as load_r2
        successor=load_r2(root)
    legal={}
    if (root/'docs/evidence/legal-001/change_boundary.json').is_file():
        from scripts.legal001_boundary import successor_hashes
        legal=successor_hashes(root)
    effective={}
    for rel,row in data['reviewed_runtime_changes'].items():
        if row['previous_sha256']!=base['files'].get(rel):
            raise ValueError('AI-005 changed source mismatch')
        if rel in successor and 'previous_sha256' in successor[rel] and successor[rel]['previous_sha256']!=row['current_sha256']:
            raise ValueError('AI-005 r2 predecessor mismatch')
        current=legal.get(rel,successor.get(rel,row)['current_sha256'])
        if not matches(root/rel,current):raise ValueError('AI-005 changed source mismatch')
        # Preserve the original predecessor for JOB-001 and older hash chains.
        effective[rel]={**row,'current_sha256':current}
    for rel,sha in data['new_runtime_sha256'].items():
        if rel in successor and 'previous_sha256' in successor[rel] and successor[rel]['previous_sha256']!=sha:
            raise ValueError('AI-005 r2 new predecessor mismatch')
        current=legal.get(rel,successor.get(rel,{}).get('current_sha256',sha))
        if not matches(root/rel,current):raise ValueError('AI-005 new runtime mismatch')
    job003 = {}
    if (root/'docs/evidence/job-003/change_boundary.json').is_file():
        from scripts.check_job003_package import successor_hashes as job003_hashes
        job003 = job003_hashes(root)
    combined = {**successor, **effective}
    for rel, row in job003.items():
        combined[rel] = ({**combined[rel], 'current_sha256': row['current_sha256']}
                         if rel in combined else row)
    return combined


def validate(root=ROOT):
    errors=[]
    try:
        load_boundary(root)
        base=json.loads((root/'docs/evidence/ai-005/baseline_files_sha256.json').read_text())['files']
        for rel,sha in base.items():
            if rel.startswith(('services/ai/','evals/','prompts/','schemas/','docs/policies/')) or rel in {
                'domain/ai.py','config.py','render.yaml','requirements.txt','requirements-dev.txt','docs/LEGAL001_DEFERRED_DECISION.md'}:
                if not matches(root/rel,sha):errors.append('Protected source changed: '+rel)
        expected_head='20261002_0023' if (root/'docs/evidence/job-003/change_boundary.json').is_file() else '20261001_0022' if (root/'docs/evidence/job-002/change_boundary.json').is_file() else '20260922_0021' if (root/'docs/evidence/legal-001/change_boundary.json').is_file() else '20260917_0020'
        if f'CURRENT_REVISION = "{expected_head}"' not in (root/'database.py').read_text():errors.append('Unexpected schema head')
        migration=(root/'migrations/versions/20260917_0020_cover_letters.py').read_text()
        tables={node.args[0].value for node in ast.walk(ast.parse(migration)) if isinstance(node,ast.Call)
                and isinstance(node.func,ast.Attribute) and node.func.attr=='create_table' and node.args and isinstance(node.args[0],ast.Constant)}
        if tables!={'cover_letters','cover_letter_versions','cover_letter_proposals'} or "down_revision = '20260917_0019'" not in migration:
            errors.append('Invalid migration')
        for rel in ('routes/cover_letters.py','services/cover_letters.py','repositories/cover_letters.py','services/cover_letter_generation.py'):
            code=(root/rel).read_text()
            if 'csrf.exempt' in code:errors.append('CSRF bypass')
            for node in ast.walk(ast.parse(code)):
                modules=[node.module or ''] if isinstance(node,ast.ImportFrom) else [n.name for n in node.names] if isinstance(node,ast.Import) else []
                if any(m.startswith(('requests','httpx','urllib.request','smtplib','services.ai.provider')) for m in modules):errors.append('Unexpected transport: '+rel)
        service=(root/'services/cover_letters.py').read_text()
        if "raise LetterError('generation_unavailable')" not in service:errors.append('Generation must remain closed')
        if 'REAL_DATA_SUPPORTED = False' not in (root/'domain/ai.py').read_text():errors.append('Real-data boundary changed')
        route=(root/'routes/cover_letters.py').read_text()
        for marker in ('g.current_user.id','email_verified_at','expected_revision','confirm','csrf_token','no-store','request.files'):
            if marker not in route:errors.append('Missing route control: '+marker)
        for f in (root/'templates/letters').glob('*.html'):
            if '|safe' in f.read_text():errors.append('Unsafe template')
        workflow=(root/'.github/workflows/ci.yml').read_text()
        if 'python scripts/check_ai005_package.py' not in workflow or 'test_ai005_routes.py' not in workflow:errors.append('Missing CI')
        for name in ('IMPLEMENTATION','RUNBOOK','VERIFICATION_STATUS','SCOPE'):
            if not (root/('docs/AI005_'+name+'.md')).is_file():errors.append('Missing AI005 documentation')
        status=(root/'docs/AI005_VERIFICATION_STATUS.md').read_text()
        for marker in ('NEEDS_VERIFICATION','LIVE_NOT_ACCEPTED','NOT RUN','20260917_0020'):
            if marker not in status:errors.append('Unproven release boundary: '+marker)
    except (OSError,ValueError,KeyError,TypeError,AttributeError,SyntaxError):
        errors.append('Missing or invalid AI-005 package evidence')
    return errors

if __name__=='__main__':
    errors=validate();print(json.dumps({'package':'AI-005','scope':'document-workflow; live generation not activated',
            'remote_ci':'not_attested_by_local_check','ok':not errors,'errors':errors},indent=2));raise SystemExit(bool(errors))
