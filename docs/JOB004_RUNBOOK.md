# JOB-004 runbook

## Local verification

1. Run `python scripts/check_job004_package.py`.
2. Run `pytest -q tests/test_job004_service.py tests/test_job004_routes.py tests/test_job004_package.py`.
3. Run inherited JOB-001/JOB-002/JOB-003 and privacy tests.
4. Run package preflight and `git diff --check`.

There is no migration, backfill, cache warm-up, provider call, external send, or rollback data operation. Rollback is application-code rollback only; schema remains `20261002_0023`.
