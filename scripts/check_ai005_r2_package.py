#!/usr/bin/env python3
"""Recorded r1 acceptance and explicit r2 boundary; never proves remote/live CI."""
from pathlib import Path
import ast
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
BASE_COMMIT='be0eadf6c26a6a45b9a3764f5859a52651f372d2'
BASE_TREE='dbcadece7814336942ea80da0ce85707a695c428'
CHANGES={'app.py','repositories/ai.py','repositories/cover_letters.py','services/cover_letters.py',
         'services/cover_letter_labels.py','routes/cover_letters.py'}
NEW_RUNTIME={'services/cover_letter_ai.py','services/ai/letter_runtime.py','services/ai/letter_contract.py',
             'services/ai/letter_admission.py','services/ai/letter_synthetic_cases.json',
             'templates/letters/generation_preview.html','scripts/ai005_synthetic_probe.py'}
EVIDENCE={'docs/evidence/ai-005-r2/change_boundary.json','docs/evidence/ai-005-r2/baseline_files_sha256.json'}

def matches(path,sha):
    raw=path.read_bytes()
    return sha in {hashlib.sha256(raw).hexdigest(),hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()}

def load_boundary(root=ROOT):
    data=json.loads((root/'docs/evidence/ai-005-r2/change_boundary.json').read_text())
    base=json.loads((root/'docs/evidence/ai-005-r2/baseline_files_sha256.json').read_text())
    if (data['package']!='AI-005' or data['release']!='r2-technical' or data['source_commit']!=BASE_COMMIT
            or data['source_tree']!=BASE_TREE or data['public_real_data_enabled'] is not False
            or set(data['reviewed_runtime_changes'])!=CHANGES or set(data['new_runtime_sha256'])!=NEW_RUNTIME
            or base['source_commit']!=BASE_COMMIT or base['source_tree']!=BASE_TREE):
        raise ValueError('Invalid AI-005 r2 scope')
    legal={}
    if (root/'docs/evidence/legal-001/change_boundary.json').is_file():
        from scripts.legal001_boundary import successor_hashes
        legal=successor_hashes(root)
    effective={}
    for rel,row in data['reviewed_runtime_changes'].items():
        current=legal.get(rel,row['current_sha256'])
        if row['previous_sha256']!=base['files'].get(rel) or not matches(root/rel,current):
            raise ValueError('AI-005 r2 predecessor/runtime mismatch')
        effective[rel]={**row,'current_sha256':current}
    for rel,sha in data['new_runtime_sha256'].items():
        current=legal.get(rel,sha)
        if rel in base['files'] or not matches(root/rel,current):raise ValueError('AI-005 r2 new source mismatch')
    return effective

def validate(root=ROOT):
    errors=[]
    try:
        load_boundary(root)
        acceptance=json.loads((root/'docs/evidence/ai-005-r1-acceptance/acceptance.json').read_text())
        if (acceptance['package']!='AI-005' or acceptance['tranche']!='r1-document-workflow'
                or acceptance['status']!='ACCEPTED_WITH_MANUAL_EXCLUSIONS'
                or acceptance['full_package_status']!='IN_PROGRESS'
                or acceptance['code_commit']!=BASE_COMMIT or acceptance['code_tree']!=BASE_TREE):
            errors.append('Invalid recorded r1 acceptance boundary')
        ci=acceptance['github']
        if (ci['run_id']!=35319097205 or ci['run_number']!=285 or ci['attempt']!=2
                or ci['head_sha']!=BASE_COMMIT or ci['conclusion']!='success'
                or ci['paid_jobs']!='skipped' or ci['exact_test_counts'] is not None):
            errors.append('Unproven CI evidence')
        if acceptance['manual_exclusions']!={'profile_proposals':'NOT RUN','two_accounts':'NOT RUN','stale_delete':'NOT SEPARATELY CONFIRMED'}:
            errors.append('Manual exclusions cannot become PASS')
        if acceptance['real_database_backup']!='NOT EVIDENCED' or acceptance['assistant_production_browser_run'] is not False:
            errors.append('Unproven operational evidence')
        if acceptance['owner_report']['schema']!='20260917_0020' or acceptance['owner_report']['final_status']!='PASS_OWNER_REPORTED':
            errors.append('Invalid owner acceptance')
        code=(root/'app.py').read_text()
        if 'COVER_LETTER_GENERATOR = CoverLetterGenerator(' not in code or 'SyntheticLetterAdmission' in code:
            errors.append('Default application admission must remain closed')
        gate=(root/'services/ai/letter_admission.py').read_text()
        if "raise LetterError('generation_unavailable')" not in gate or 'os.environ' in gate:
            errors.append('Legal gate cannot be an environment boolean')
        if 'REAL_DATA_SUPPORTED = False' not in (root/'domain/ai.py').read_text():errors.append('Real data enabled')
        for rel in NEW_RUNTIME|CHANGES:
            if rel.endswith('.py'):
                tree=ast.parse((root/rel).read_text())
                if any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='exempt' for n in ast.walk(tree)):
                    errors.append('Unexpected exemption '+rel)
        preview=(root/'templates/letters/generation_preview.html').read_text()
        if '|safe' in preview or 'csrf_token()' not in preview or 'name="confirm"' not in preview:errors.append('Unsafe preview')
        workflow=(root/'.github/workflows/ci.yml').read_text()
        if 'python scripts/check_ai005_r2_package.py' not in workflow or 'test_ai005_live_routes.py' not in workflow:errors.append('Missing r2 CI')
        for rel in ('docs/PLAN_CURRENT.md','docs/AI005_SCOPE.md','docs/AI005_VERIFICATION_STATUS.md'):
            source=(root/rel).read_text()
            if 'IN_PROGRESS' not in source or 'LIVE_NOT_ACCEPTED' not in source:errors.append('Unproven final acceptance '+rel)
    except (OSError,ValueError,KeyError,TypeError,SyntaxError):errors.append('Missing or invalid AI-005 r2 evidence')
    return errors

if __name__=='__main__':
    errors=validate();print(json.dumps({'package':'AI-005','release':'r2-technical','ok':not errors,
         'remote_ci':'NOT RUN for r2','live_quality':'NOT RUN','errors':errors},indent=2));raise SystemExit(bool(errors))
