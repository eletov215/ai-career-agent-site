# AI Career Agent - AI-001 / Verification status

| Поле | Значение |
|---|---|
| Document | AI001_VERIFICATION_STATUS |
| Version | 1.2 |
| Date | 2026-09-15 |
| Package | AI-001 |
| Status | **ВЫПОЛНЕНО**; synthetic-only foundation accepted, public AI disabled |
| Verified schema | `20260914_0015` |
| Verified deployed revision | `bc177dd6b970750f556f48f34dbd022a30e80a34` |

## 1. Decision

AI-001 is **COMPLETE within its documented synthetic-only technical boundary**. The completion decision is based on the previously recorded local verification, GitHub CI #266 and the owner-confirmed staging/manual-mode smoke. It is not legal clearance and does not authorize real-user AI traffic.

## 2. Local evidence retained from the candidate

| Check | Measured result | Boundary |
|---|---|---|
| Full available pytest | 495 passed; 17 skipped; 82 subtests passed; 0 failed | Local dependency set, not full CI |
| AI-001 focused tests | 80 passed; 3 skipped | Subset of full suite |
| Provider policy tests | 47 passed | Subset of full suite |
| Accepted benchmark tests | 90 passed | Subset of full suite |
| SQLite migration `0014 -> 0015 -> 0014 -> 0015` | PASS | Seven additive AI tables checked |
| Package gates | PASS | No live provider call |

The CI hotfix then corrected the dependency-free package checker so that it no longer imports production SQLAlchemy paths. Regression coverage was added for this boundary.

## 3. External acceptance / GitHub CI #266

| Gate | Result |
|---|---|
| Workflow | **Success**, 5m25s |
| Python tests | **Success**, 5m21s |
| AI-BENCH-001 package gate | **Success**, 7s |
| Alice Final | Skipped as intended |
| Live Yandex | Skipped as intended |

This closes the previously failing package-gate issue (`ModuleNotFoundError: sqlalchemy`) without adding SQLAlchemy to the isolated benchmark job.

## 4. Staging acceptance

`/health/ready` evidence supplied by the owner confirms:

- `status=ok`;
- PostgreSQL `persistent=true`;
- `database.revision=20260914_0015`;
- `current_revision=expected_revision=20260914_0015`;
- `migrations.ok=true`;
- privacy worker enabled/alive with `last_status=ok`;
- deployed version `bc177dd6b970750f556f48f34dbd022a30e80a34`.

`/api/ai/status` confirms the intended fail-closed state:

```json
{
  "ok": true,
  "generation_available": false,
  "mode": "manual",
  "reason": "runtime_not_activated",
  "notice_key": "ai_temporarily_unavailable_manual_mode"
}
```

The owner confirmed that the manual-mode banner is visible and vacancy search plus the remaining checked site functions continue to work normally.

## 5. Accepted scope

AI-001 completion covers:

- provider-neutral AI runtime interface;
- Alice adapter behind closed activation gates;
- strict synthetic fixture/schema registry;
- central technical cost/request/concurrency limits;
- durable reservations, idempotency and accounting;
- bounded retries/deadlines and provider circuit state;
- read-only status endpoint and explicit manual fallback;
- migration `20260914_0015` with seven additive AI tables.

## 6. Explicit exclusions

Still **not authorized or not implemented as accepted product functionality**:

- sending real resume/profile content to Alice;
- public generation endpoints;
- paid subscriptions or plan enforcement;
- final Free/Standard/Max quotas;
- final LEGAL-001 operator/consent/data-location decisions;
- AI-002 actual resume analysis;
- a new paid Alice transport run for this package.

## 7. Rollback boundary

The previous application revision expects schema `0014`; reverting the application while leaving `0015` is not a guaranteed safe rollback. Follow AI001_RUNBOOK: stop admissions, preserve accounting metadata and verified backup, then perform a controlled downgrade only when explicitly required.

## 8. Next action

AI-002 is **ГОТОВО К СТАРТУ ПОСЛЕ СВЕЖЕГО ZIP**. The owner must upload the current GitHub `main` archive before any code modifications. LEGAL-001 must return before public real-data AI, paid subscriptions or commercial release.

## 9. Version log

| Version | Date | Change |
|---|---|---|
| 1.2 | 2026-09-15 | AI-001 accepted after CI #266 + staging0015 + manual/core smoke |
| 1.1 | 2026-09-14 | Synthetic-only candidate and local evidence; external gates pending |
