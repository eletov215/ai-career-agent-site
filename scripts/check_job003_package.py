#!/usr/bin/env python3
"""Fail-closed JOB-003 successor and safety boundary."""
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE='docs/evidence/job-003/change_boundary.json'
REVIEWED_RUNTIME_CHANGES={
    'app.py','database.py','models/__init__.py','operations/backup.py',
    'repositories/privacy.py','routes/application_trackers.py','services/privacy.py',
    'services/storage.py','templates/application_trackers/detail.html','templates/dashboard.html',
}
NEW_RUNTIME={
    'domain/reminders.py','migrations/versions/20261002_0023_in_app_reminders.py',
    'models/reminder.py','repositories/reminders.py','routes/reminders.py',
    'services/reminders.py','templates/reminders/error.html','templates/reminders/index.html',
}
AUTHORIZED_GUARD_CHANGES={
    'scripts/check_ai001_package.py','scripts/check_ai002_package.py',
    'scripts/check_ai003_package.py','scripts/check_ai004_package.py',
    'scripts/check_ai005_package.py','scripts/check_job001_package.py',
    'scripts/check_job002_package.py','scripts/check_legal001_package.py',
}
def digest(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def successor_hashes(root=ROOT):
        e=json.loads((root/EVIDENCE).read_text())
        expected={'package':'JOB-003','source_commit':'8001efbd4c70144bdeab2bdf8e3f64b00bf9c179','source_tree':'1248fd93e4a488d6cab1ae757880432ccb2da35b','schema_from':'20261001_0022','schema_to':'20261002_0023','legal_state':'DRAFT','public_real_data_enabled':False,'provider_calls':0,'production_migration':'NOT_RUN'}
        for k,v in expected.items():
            if e.get(k)!=v: raise ValueError('evidence:'+k)
        if set(e.get('reviewed_runtime_changes',{})) != REVIEWED_RUNTIME_CHANGES: raise ValueError('scope:reviewed_runtime_changes')
        if set(e.get('new_runtime_sha256',{})) != NEW_RUNTIME: raise ValueError('scope:new_runtime_sha256')
        if set(e.get('authorized_guard_changes',{})) != AUTHORIZED_GUARD_CHANGES: raise ValueError('scope:authorized_guard_changes')
        successor_path=root/'docs/evidence/job-004/change_boundary.json'
        if successor_path.is_file() and (root/'scripts/check_job004_package.py').is_file():
            try: from scripts.check_job004_package import successor_hashes as job004_hashes
            except ModuleNotFoundError:
                from check_job004_package import successor_hashes as job004_hashes
            authorized=job004_hashes(root)
        else: authorized={}
        from scripts.ai004_m04b_successor import approved_sha256
        effective={}
        for p,row in e['reviewed_runtime_changes'].items():
            next_row=authorized.get(p,{})
            if set(row)!={'previous_sha256','current_sha256'}:
                raise ValueError('scope:'+p)
            if next_row and next_row.get('previous_sha256') != row['current_sha256']:
                raise ValueError('successor_parent:'+p)
            predecessor = next_row.get('current_sha256',row['current_sha256'])
            verified = approved_sha256(root,p,predecessor)
            if hashlib.sha256((root/p).read_bytes()).hexdigest()!=verified:
                raise ValueError('hash:'+p)
            effective[p]={**row,'current_sha256':verified}
        for p,value in e['new_runtime_sha256'].items():
            if hashlib.sha256((root/p).read_bytes()).hexdigest()!=value: raise ValueError('hash:'+p)
        guards={}
        for p,row in e['authorized_guard_changes'].items():
            if set(row)!={'previous_sha256','current_sha256'}:
                raise ValueError('guard_scope:'+p)
            verified=approved_sha256(root,p,row['current_sha256'])
            if hashlib.sha256((root/p).read_bytes()).hexdigest()!=verified:
                raise ValueError('hash:'+p)
            guards[p]={**row,'current_sha256':verified}
        return {**authorized,**effective,**guards}
def validate():
    errors=[]
    try:
        successor_hashes(ROOT)
        from scripts.ai004_m04b_successor import expected_schema_head
        approved_head = expected_schema_head(ROOT, "20261002_0023")
        checks={'database.py':f'CURRENT_REVISION = "{approved_head}"','domain/ai.py':'REAL_DATA_SUPPORTED = False','services/legal_policy.py':'release_state="DRAFT"','migrations/versions/20261002_0023_in_app_reminders.py':"down_revision = '20261001_0022'"}
        for p,n in checks.items():
            if n not in (ROOT/p).read_text(): errors.append('boundary:'+p)
        forbidden=('requests.','email_delivery','provider_operation','smtplib','httpx')
        for p in ('services/reminders.py','routes/reminders.py','repositories/reminders.py'):
            if any(x in (ROOT/p).read_text() for x in forbidden): errors.append('dispatch:'+p)
    except Exception as exc: errors.append('guard:'+str(exc))
    return errors
if __name__=='__main__':
    failures=validate(); print(json.dumps({'package':'JOB-003','ok':not failures,'errors':failures,'provider_calls':0,'production_migration':'NOT_RUN','remote_ci':'NOT_ATTESTED_BY_LOCAL_CHECK'},indent=2)); raise SystemExit(bool(failures))
