# LEGAL-001 Runbook

Status: NEEDS_VERIFICATION.

Verification sequence:

1. Confirm branch is based on `f5ce1f42836e3872854332324f2ebdd9c8934b36`.
2. Run `python scripts/check_legal001_package.py`.
3. Run focused tests: migration, service/repository, routes, admission and package.
4. Run existing AI-005/JOB/PRIV regression gates and full relevant pytest.
5. Push branch and verify GitHub CI head SHA matches the candidate commit.
6. Do not merge on red CI.
7. After merge/deploy, verify `/health/ready` reports `20260922_0021`.
8. Production QA may use only the existing verified account with synthetic QA data.

Acceptance must not enable Alice real-data traffic. No environment variable is an activation path. A future reviewed code change plus final legal/owner decisions are required before any limited real-data test.
