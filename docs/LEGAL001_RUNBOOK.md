# LEGAL-001 Runbook

Status: CI_PASS / DEPLOYMENT_AND_PRODUCTION_QA_PENDING.

Verification sequence:

1. Confirm branch is based on `f5ce1f42836e3872854332324f2ebdd9c8934b36`.
2. Run `python scripts/check_legal001_package.py`.
3. Run focused tests: migration, service/repository, routes, admission and package.
4. Run existing AI-005/JOB/PRIV regression gates and full relevant pytest.
5. Branch CI #304 on `fe3a7e1b553ccc9ebb5b956efce3779287291c04` is SUCCESS; dedicated LEGAL-001, PostgreSQL/migrations, AI-005 r2 no-paid-call gate and full Run tests passed.
6. For any later code/doc-sync commit, require green CI again before merge.
7. After merge/deploy, verify `/health/ready` reports `20260922_0021`.
8. Production QA may use only the existing verified account with synthetic QA data.

Acceptance must not enable Alice real-data traffic. No environment variable is an activation path. A future reviewed code change plus final legal/owner decisions are required before any limited real-data test.
