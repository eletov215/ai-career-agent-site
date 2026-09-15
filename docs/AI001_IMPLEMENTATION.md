# AI Career Agent - AI-001 / Runtime foundation

| Поле | Значение |
|---|---|
| Document | AI001_IMPLEMENTATION |
| Version | 1.2 |
| Date | 2026-09-15 |
| Package | AI-001 |
| Status | **ВЫПОЛНЕНО** within synthetic-only boundary; public AI disabled |
| Verified schema | 20260914_0015 on Render/Neon staging |

## 1. Purpose and scope

AI-001 prepares the provider-independent runtime for later feature packages. It does not replace the existing deterministic PDF parser or implement real resume analysis, interview, matching or letters. The owner postponed LEGAL-001; real-data/public generation is deliberately unavailable.

`AIRequest(user_id, idempotency_key, fixture_id)` accepts only an ID of one of eight pinned synthetic fixtures. No arbitrary prompt, uploaded resume, database profile, filename or URL may enter this interface. Tests inject a fake provider; no billable request was made for this release.

## 2. Architecture

```text
Pinned synthetic request
  -> deployment gates + exact fixture/schema registry
  -> atomic policy/budget/concurrency admission
  -> provider-neutral interface -> qualified Alice adapter
  -> bounded child-process HTTP attempt (at most two attempts)
  -> strict JSON/schema validation
  -> atomic usage settlement -> structured result or manual state
```

| Layer | Files / responsibility |
|---|---|
| Domain | `domain/ai.py`: request/result/provider interface and safe errors |
| Orchestration | `services/ai/service.py`: ordered gates, retries and settlement |
| Transport | `services/ai/provider.py`, `_http_worker.py`: fixed endpoint, no redirects, no SDK retries |
| Contracts | `registry.py`, pinned prompts/schemas and hash manifest |
| Persistence | `models/ai.py`, `repositories/ai.py`: seven tables and transaction boundary |
| Operations | `scripts/manage_ai_runtime.py`: version-checked central technical controls |
| Public state | `routes/ai_status.py`, shared manual notice; no generation POST route |

## 3. Closed activation boundary

Safe environment defaults are `AI_ENABLED=0`, `AI_KILL_SWITCH=1`, `AI_SYNTHETIC_ACCESS_ENABLED=0`. DB defaults also have enabled=false and kill_switch=true. Exact model/folder credentials and a recorded no-logging disablement time at least24hours old are checked before any internally authorized synthetic call.

These controls do NOT authorize real personal data. `REAL_DATA_SUPPORTED=False` and the fixture-only API remain hard boundaries even when synthetic gates are deliberately opened in a separate controlled environment. There is no `AI_LEGAL_APPROVED` boolean bypass. Provider no-logging evidence must be genuine; this implementation cannot prove that an operator-entered timestamp corresponds to a provider-side action.

## 4. Cost and execution guards

All counts and money are stored durably; costs use integer micro-RUB, not floating point. Admission locks the singleton policy row on PostgreSQL; SQLite uses BEGIN IMMEDIATE. No network call runs inside this transaction.

Before dispatch, all potential attempts are reserved against user-day/global-day/global-month budgets. A logical request consumes one technical request counter regardless of retries. Actual known usage replaces the reservation; unknown usage remains conservatively counted. An observed token/cost overrun activates the DB kill switch. Changing prices during an in-flight request does not alter its recorded rate snapshot.

The provider attempt runs in a short-lived child process. Parent wall-clock timeout covers DNS, connect and response reading. A child watchdog also exits if its parent disappears. HTTP socket timeouts alone are not treated as total deadlines. Idempotency, anonymous capacity leases and persisted circuit state protect process restarts and concurrent calls.

## 5. Commercial separation

Migration seeds no Free/Standard/Max plans or allowances. Commercial enforcement is disabled. The lookup tables and optional action reservation logic are separate from technical safety caps. A failed operation consumes no successful commercial action, even where upstream tokens have a cost. Technical-only successes do not retrospectively spend a commercial quota when enforcement is later enabled.

No paid subscription, account upgrade, commercial UI or payment provider is added. BILL-001 owns those decisions. Operator CLI values are not customer promises.

## 6. Data, output and privacy

The ledger contains UUIDs, task/language/fixture IDs, version/hash metadata, counters, timestamps and conservative cost estimates. It has no prompt/response, email, contact or resume-content column. Idempotency fingerprints use a server HMAC. No raw provider bodies or credentials are logged.

Strict JSON validation rejects invalid syntax, duplicate keys, non-finite constants, missing fields and schema violations. This is NOT a complete semantic grounding test for future real profiles. Accepted writing discipline is retained in pinned prompts; future features still need feature-specific grounding/evaluation.

Owner export includes bounded metadata. Deletion cascades user events/plans/buckets; global aggregates and opaque short-lived capacity leases remain to avoid budget/concurrency bypass. Metadata defaults to30days with bounded cleanup; current-month global budgets are not erased mid-period. Unknown outcomes are not silently refunded.

## 7. Database and deployment

Migration0015 adds `ai_runtime_policies`, `ai_usage_events`, `ai_budget_buckets`, `ai_request_leases`, `ai_provider_states`, `ai_plan_entitlements`, `ai_user_plans`. Existing tables/data are not rewritten. Backup inventory includes all seven.

Deployment acceptance is now recorded: GitHub CI #266 passed and Render/Neon staging reports current=expected `20260914_0015`, `migrations.ok=true`, deployed version `bc177dd6b970750f556f48f34dbd022a30e80a34`. `/api/ai/status` remains fail-closed (`generation_available=false`, `mode=manual`). Follow AI001_RUNBOOK for rollback; do not enable provider secrets or real-data entry points as part of this closure.

## 8. Limitations and next step

Input admission uses a character-based estimate on the fixed synthetic payloads, not an exact vendor tokenizer. A full cap is reserved and actual overrun stops further admissions, but the preflight estimate is not a guaranteed upstream token cap. Idempotent duplicate results return metadata, not cached response text. Reconciliation of uncertain provider charges and real-data result persistence are future operational/feature work.

Policy serialization is intentionally conservative for a small beta; multi-region/high-throughput scaling is not claimed. New PostgreSQL/Flask execution is an external gate where dependencies are unavailable locally. AI-001 is complete only for this synthetic-only technical foundation; LEGAL-001 remains mandatory before public real-data AI, subscriptions or release.

## 9. Version log

1.2 / 2026-09-15: external acceptance recorded from CI #266 + staging0015/manual/core smoke; public AI remains disabled.

1.1 / 2026-09-14: verified synthetic-only candidate and measured seven-table implementation; unpublished earlier drafts superseded.
