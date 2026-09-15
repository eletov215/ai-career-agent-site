# AI Career Agent - AI-001 / Runtime reference

| Поле | Значение |
|---|---|
| Document | AI001_RUNTIME_REFERENCE |
| Version | 1.2 |
| Date | 2026-09-15 |
| Package | AI-001 |
| Status | AI-001 ВЫПОЛНЕНО; public AI disabled |
| Verified schema | 20260914_0015 on staging |

## 1. Central policy defaults

| Control | Value | Meaning |
|---|---:|---|
| enabled / kill_switch | false / true | DB gates closed |
| Commercial enforcement | false | No plan quotas seeded |
| User / global logical requests per day | 100 / 1000 | Technical counts, not tariff |
| User budget per day | 200 RUB | Internal guard |
| Global day / month budget | 1000 / 20000 RUB | Internal guards |
| User / global concurrency | 1 / 2 | Durable in-flight capacity |
| Input estimate / output cap | 8000 / 1600 tokens | Input is estimated; actual overrun halts AI |
| Maximum attempts | 2 | Retries included in reservation |
| Attempt / orchestration deadline | 25 / 55 seconds | Ledger/lock overhead is additional |
| Lease | 90 seconds | Recovers interrupted requests conservatively |
| Circuit threshold / cooldown | 3 / 60 seconds | Single half-open probe |
| Metadata retention | 30 days | Technical default; future legal review |
| Pricing check validity | 30 days | Stale snapshot denies admission |

Rates from the approved2026-09-14 snapshot are500 micro-RUB/input token and1200 micro-RUB/output token. These are estimates, not a provider invoice. One maximum attempt reserves5.92RUB; two reserve11.84RUB. Changing a policy version affects subsequent admissions only. UTC defines day/month boundaries.

## 2. States and accounting

`reserved`: worst-case spend and capacity admitted. `succeeded`: strict schema passed and settlement completed. `failed`: known terminal result; known upstream costs still recorded. `unknown`: interrupted/ambiguous usage conservatively retained. A failed business result is not necessarily a free provider call.

Only successful requests admitted with commercial enforcement consume a future monthly feature action. No commercial amount is charged to a payment method. Expired reservations remain counted; do not reset counters to hide uncertainty.

## 3. Mutating limits without code changes

Run in a trusted server shell with existing DATABASE_URL, never by exposing it in chat:

```bash
python scripts/manage_ai_runtime.py show
python scripts/manage_ai_runtime.py set --expected-version 1 --user-daily-budget-rub 250
python scripts/manage_ai_runtime.py show
```

Use the actual version returned by show, not the example1. A stale expected-version is rejected. Change global caps similarly with `--global-daily-budget-rub` and `--global-monthly-budget-rub`; stop admissions with `--kill-switch on`. The CLI cannot accept provider secrets or tariff quotas. No web admin panel is promised in this package.

A DB policy update is visible on subsequent admission without redeployment. Environment values are process configuration and require restart if changed. An in-flight provider request cannot be recalled; switching off prevents the next dispatch/retry and new admissions.

## 4. Environment variables

```text
AI_ENABLED=0
AI_KILL_SWITCH=1
AI_SYNTHETIC_ACCESS_ENABLED=0
```

Optional credentials for a future explicitly authorized synthetic-only test: AI_YANDEX_API_KEY, AI_YANDEX_FOLDER_ID, AI_YANDEX_MODEL_URI. Exact qualified model: `gpt://<folder>/aliceai-llm/latest`. AI_NO_LOGGING_DISABLED_AT must be a timezone-aware ISO timestamp of the real opt-out action, not an invented date. Never add these keys for ordinary acceptance.

Metadata retention, money caps and circuit settings live in the central DB policy, not fabricated environment knobs. There is no AI_LEGAL_APPROVED flag in this build.

## 5. Public state

`GET /api/ai/status` is read-only, rate-limited and no-store. It returns ok, generation_available=false, mode=manual, reason=runtime_not_activated, notice_key and a Russian notice. It exposes no model/folder credentials or user IDs and never probes the provider. No POST endpoint exists.

## 6. Recovery and cleanup

```bash
python scripts/manage_ai_runtime.py recover
python scripts/manage_ai_runtime.py cleanup
```

Recovery marks stale reserved events unknown; it does not invent zero cost. Cleanup is also called by the existing privacy worker. User deletion removes owned metadata but not identifier-free global spend or unexpired opaque capacity leases. These measures protect against deletion/re-registration bypass of global ceilings, not a complete anti-abuse system.

## 7. Verified staging state / 2026-09-15

GitHub CI #266 and Render/Neon smoke accepted this runtime with schema `20260914_0015`. Public state remains intentionally closed: `generation_available=false`, `mode=manual`, `reason=runtime_not_activated`. The manual notice is visible in the UI and vacancy search remains unaffected.

These technical caps remain safety controls, not subscription promises. AI-002 may build on them after the current GitHub ZIP is inspected.

## 8. Version log

1.2 / 2026-09-15: staging0015/manual-mode acceptance recorded; limits unchanged.

1.1 / 2026-09-14: actual defaults, CLI version checks, token-estimate limitation and separate future entitlement accounting.
