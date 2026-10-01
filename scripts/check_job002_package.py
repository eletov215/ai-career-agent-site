#!/usr/bin/env python3
"""Fail-closed JOB-002 package boundary without altering predecessor evidence."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED={
 'domain/application_tracker.py','models/application_tracker.py','repositories/application_trackers.py',
 'services/application_trackers.py','routes/application_trackers.py',
 'migrations/versions/20261001_0022_application_tracker.py','templates/application_trackers/detail.html',
 'tests/test_job002_service.py','tests/test_job002_routes.py','tests/test_job002_migration.py',
 'docs/JOB002_IMPLEMENTATION.md','docs/JOB002_RUNBOOK.md','docs/JOB002_VERIFICATION_STATUS.md',
 'docs/evidence/job-002/change_boundary.json'}


def validate():
    errors=[f'missing:{path}' for path in sorted(REQUIRED) if not (ROOT/path).is_file()]
    checks={'database.py':'CURRENT_REVISION = "20261001_0022"',
            'domain/ai.py':'REAL_DATA_SUPPORTED = False',
            'migrations/versions/20261001_0022_application_tracker.py':"down_revision = '20260922_0021'"}
    for path,needle in checks.items():
        if needle not in (ROOT/path).read_text():errors.append(f'boundary:{path}')
    if not (ROOT/'docs/evidence/job-001/change_boundary.json').is_file():errors.append('predecessor_evidence_missing')
    return errors


if __name__=='__main__':
    errors=validate();print(json.dumps({'package':'JOB-002','ok':not errors,'errors':errors},indent=2));raise SystemExit(bool(errors))
