# JOB-002 runbook

## Local verification

1. Run `python scripts/check_job002_package.py`.
2. Run `python -m pytest -q tests/test_job002_service.py tests/test_job002_routes.py tests/test_job002_migration.py tests/test_job002_package.py`.
3. Run affected JOB-001, PRIV-001, migration, backup and historical package checks.

## Release boundary

Do not run the production migration from this package task. Before a later owner-approved deployment, record and confirm a Neon recovery point, then use the normal migration release path. Do not change Render configuration or secrets. Downgrade removes tracker history and therefore requires an explicit rollback decision and verified recovery point.
