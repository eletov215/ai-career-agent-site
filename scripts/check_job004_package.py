#!/usr/bin/env python3
"""Fail-closed JOB-004 no-migration successor boundary."""
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE='docs/evidence/job-004/change_boundary.json'
REVIEWED_RUNTIME={'app.py','services/storage.py','templates/dashboard.html','scripts/check_job003_package.py',
                  'tests/ai005_boundary_helper.py'}
NEW_RUNTIME={'repositories/job_analytics.py','services/job_analytics.py','routes/job_analytics.py','templates/analytics/index.html'}
SUPPORT={'tests/test_job004_service.py','tests/test_job004_routes.py','tests/test_job004_package.py',
         'docs/JOB004_IMPLEMENTATION.md','docs/JOB004_RUNBOOK.md','docs/JOB004_VERIFICATION_STATUS.md',
         '.github/workflows/job004.yml','scripts/check_job004_package.py'}

def digest(root,path): return hashlib.sha256((root/path).read_bytes()).hexdigest()

def successor_hashes(root=ROOT):
    evidence=json.loads((root/EVIDENCE).read_text())
    expected={'package':'JOB-004','source_commit':'a446593e93e2bb94bc9c222f4ed66c431593d2b7',
              'source_tree':'dc02f00ee8e11be09334003ef9ee8fa891adee46','schema_from':'20261002_0023',
              'schema_to':'20261002_0023','legal_state':'DRAFT','public_real_data_enabled':False,
              'provider_calls':0,'production_migration':'NOT_APPLICABLE'}
    for key,value in expected.items():
        if evidence.get(key)!=value: raise ValueError('evidence:'+key)
    for section,paths in [('reviewed_runtime_changes',REVIEWED_RUNTIME),('new_runtime_sha256',NEW_RUNTIME),('support_sha256',SUPPORT)]:
        if set(evidence.get(section,{}))!=paths: raise ValueError('scope:'+section)
    for path,row in evidence['reviewed_runtime_changes'].items():
        if set(row)!={'previous_sha256','current_sha256'} or digest(root,path)!=row['current_sha256']:
            raise ValueError('hash:'+path)
    for section in ('new_runtime_sha256','support_sha256'):
        for path,value in evidence[section].items():
            if digest(root,path)!=value: raise ValueError('hash:'+path)
    return evidence['reviewed_runtime_changes']

def validate(root=ROOT):
    errors=[]
    try:
        successor_hashes(root)
        if 'CURRENT_REVISION = "20261002_0023"' not in (root/'database.py').read_text(): errors.append('revision')
        if 'REAL_DATA_SUPPORTED = False' not in (root/'domain/ai.py').read_text(): errors.append('real_data')
        if 'release_state="DRAFT"' not in (root/'services/legal_policy.py').read_text(): errors.append('legal')
        if any((root/'migrations/versions').glob('*job004*')): errors.append('migration')
        forbidden=('requests.','httpx','provider_operation','email_delivery','snapshot_json')
        for path in NEW_RUNTIME:
            if any(term in (root/path).read_text() for term in forbidden): errors.append('dispatch_or_snapshot:'+path)
    except Exception as exc: errors.append('guard:'+str(exc))
    return errors

if __name__=='__main__':
    failures=validate(); print(json.dumps({'package':'JOB-004','ok':not failures,'errors':failures,
        'provider_calls':0,'production_migration':'NOT_APPLICABLE','remote_ci':'NOT_ATTESTED_BY_LOCAL_CHECK'},indent=2)); raise SystemExit(bool(failures))
