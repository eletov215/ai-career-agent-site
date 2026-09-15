# AI Career Agent - AI-001 / Verification and rollback

| Поле | Значение |
|---|---|
| Document | AI001_RUNBOOK |
| Version | 1.2 |
| Date | 2026-09-15 |
| Package | AI-001 |
| Status | AI-001 ВЫПОЛНЕНО; operational rollback reference; public AI disabled |
| Verified schema | 20260914_0015 on staging |

## 1. Source and local checks

Use PATCH over an unchanged main(31) baseline; do not delete the project directory. Do not apply the abandoned LEGAL candidate or any unpublished1.4.52 package.

```bash
python scripts/check_ai001_package.py
python scripts/check_ai_provider_package.py
python scripts/check_ai_bench_package.py
python -m pytest -q tests/test_ai001_*.py
python scripts/check_document_structure.py
python scripts/check_repository_hygiene.py
```

Ordinary CI must run the dedicated AI-001 step plus existing regressions, PostgreSQL integration, encrypted backup/restore and container checks. A previous green provider CI does not prove this candidate. Leave both paid Alice/Yandex workflow inputs false.

## 2. Before changing staging

Preserve a verified backup of existing staging data using the existing backup/restore procedure. The new schema is additive, but a backup is still the rollback prerequisite. Do not send database credentials or dumps through chat. Actual production restore drill remains OPS-002/REL-001; it is not retroactively claimed here.

No provider keys or payment are needed. Keep AI_ENABLED=0, AI_KILL_SWITCH=1 and AI_SYNTHETIC_ACCESS_ENABLED=0 (absent values also resolve to these defaults). Leave the current Neon DATABASE_URL unchanged. Existing Render start command performs migrations before starting web/workers.

## 3. External acceptance - completed 2026-09-15

GitHub CI #266 passed. Staging readiness confirms PostgreSQL persistent=true, status=ok, `current_revision=expected_revision=20260914_0015`, `migrations.ok=true`, privacy worker alive/ok and deployed version `bc177dd6b970750f556f48f34dbd022a30e80a34`.

`/api/ai/status` confirms `generation_available=false`, `mode=manual`, `reason=runtime_not_activated`. The owner confirmed the manual-mode notice is visible and vacancy search plus the remaining checked site functions work normally. No paid provider call was part of this acceptance.

Keep these checks as the baseline for future AI-002 regressions. A future feature package must not silently enable public generation.

## 4. Operator policy test

No need to raise budgets to accept this package. On a disposable test database, show the policy, adjust one technical cap with expected-version, show it again, reject a stale version, then restore the prior value. Keep DB enabled=false and kill_switch=true throughout.

Tests cover fake-provider success, timeout, schema failure, retries, idempotency, circuit, atomic reservations, interrupted recovery, deletion and quota separation. Real Alice connectivity for this newly implemented transport is NOT attested by the old benchmark; any later synthetic paid test needs separate explicit authorization and no-logging prerequisites.

## 5. Rollback

First disable admissions and stop the new writers. Export/retain any new AI accounting metadata and verify a database backup. The prior application expects exact schema0014, so leaving0015 while reverting to the old build can fail readiness.

Only after the above preparation and an explicit rollback decision run a controlled downgrade to20260819_0014, then deploy the prior compatible application. Downgrade drops all seven AI tables and is destructive for their contents. Existing account/profile/resume/source tables are not dropped by this migration. Never use a database reset as rollback.

## 6. Next gate

AI-001 is accepted. Continue AI-002 only after a fresh current GitHub ZIP is supplied and inspected. LEGAL-001 must be completed before real-user AI, paid subscriptions or commercial release; deployment success is not legal approval.

## 7. Version log

1.2 / 2026-09-15: CI #266 and staging0015/manual-mode acceptance recorded; runbook retained for rollback and AI-002 regression baseline.

1.1 / 2026-09-14: synthetic-only deploy acceptance and exact-revision rollback procedure.
