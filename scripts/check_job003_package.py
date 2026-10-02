#!/usr/bin/env python3
"""Fail-closed JOB-003 successor and safety boundary."""
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE='docs/evidence/job-003/change_boundary.json'
def digest(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def validate():
    errors=[]
    try:
        e=json.loads((ROOT/EVIDENCE).read_text())
        expected={'package':'JOB-003','source_commit':'8001efbd4c70144bdeab2bdf8e3f64b00bf9c179','source_tree':'1248fd93e4a488d6cab1ae757880432ccb2da35b','schema_from':'20261001_0022','schema_to':'20261002_0023','legal_state':'DRAFT','public_real_data_enabled':False,'provider_calls':0,'production_migration':'NOT_RUN'}
        for k,v in expected.items():
            if e.get(k)!=v: errors.append('evidence:'+k)
        for p,row in e['reviewed_runtime_changes'].items():
            if set(row)!={'previous_sha256','current_sha256'} or digest(p)!=row['current_sha256']: errors.append('hash:'+p)
        for p,value in e['new_runtime_sha256'].items():
            if digest(p)!=value: errors.append('hash:'+p)
        for p,row in e['authorized_guard_changes'].items():
            if set(row)!={'previous_sha256','current_sha256'} or digest(p)!=row['current_sha256']: errors.append('hash:'+p)
        checks={'database.py':'CURRENT_REVISION = "20261002_0023"','domain/ai.py':'REAL_DATA_SUPPORTED = False','services/legal_policy.py':'release_state="DRAFT"','migrations/versions/20261002_0023_in_app_reminders.py':"down_revision = '20261001_0022'"}
        for p,n in checks.items():
            if n not in (ROOT/p).read_text(): errors.append('boundary:'+p)
        forbidden=('requests.','email_delivery','provider_operation','smtplib','httpx')
        for p in ('services/reminders.py','routes/reminders.py','repositories/reminders.py'):
            if any(x in (ROOT/p).read_text() for x in forbidden): errors.append('dispatch:'+p)
    except Exception as exc: errors.append('guard:'+str(exc))
    return errors
if __name__=='__main__':
    failures=validate(); print(json.dumps({'package':'JOB-003','ok':not failures,'errors':failures,'provider_calls':0,'production_migration':'NOT_RUN','remote_ci':'NOT_ATTESTED_BY_LOCAL_CHECK'},indent=2)); raise SystemExit(bool(failures))
