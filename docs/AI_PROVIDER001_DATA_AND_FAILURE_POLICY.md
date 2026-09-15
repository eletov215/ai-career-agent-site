# AI Career Agent - AI-PROVIDER-001 / Data and failure policy

| Поле | Значение |
|---|---|
| Document | AI_PROVIDER001_DATA_AND_FAILURE_POLICY |
| Package | AI-PROVIDER-001 |
| Version | 1.2 |
| Date | 2026-09-14 |
| Status | УТВЕРЖДЕНО ВЛАДЕЛЬЦЕМ; ordinary GitHub CI #262 green; package complete |
| Scope | Architecture and offline validation only; no production AI activation |
| Schema revision | 20260819_0014 (unchanged) |

## 1. Boundary and data flow

All controls in this document are requirements for AI-001 unless explicitly described as existing. They are not enabled merely by committing this architecture package.

Future flow: authenticated owner -> purpose-specific consent/authorization -> confirmed profile snapshot + bounded vacancy facts -> minimized task payload -> admitted/budgeted server-side provider call -> schema and grounding checks -> clean presentation -> explicit owner save. Reject invalid or incomplete output without overwriting an existing document or promoting suggestions into confirmed PROF-001 facts.

Send only relevant, manually confirmed career facts and the task's required vacancy facts. Use task-local evidence IDs, not database user IDs. Omit names/contact details, precise address, birth date, photo, raw PDFs, OAuth payloads and secrets. Do not send special-category, biometric or protected-secret content. Remove identifiers from public vacancy/contact fields too. De-identification reduces exposure but does not automatically make a career history anonymous; LEGAL-001 must assess remaining personal data.

Vacancy text and user text are untrusted data, not instructions with authority to change the system prompt, choose an endpoint, enable tools or reveal secrets. No browsing, files, provider storage, tools, autonomous actions or embeddings are in the initial scope. No cross-user generation cache.

## 2. Logging, retention and the 24-hour prerequisite

Technical no-logging instructions [S4] and the contractual timing [S5, section 5.5] must both be respected. **Proposed conservative activation rule:** attach `x-data-logging-enabled: false` to every call, establish the correct opt-out procedure for the selected API/account, record its confirmation time and allow at least 24 hours before real personal-data requests. A timer alone is not proof that the procedure was correctly performed. Clarify scope with provider support when necessary.

The current opt-out confirmation timestamp is unknown. Existing benchmark calls used synthetic fixtures and did not establish this production control. Production activation remains blocked; a new paid benchmark is not needed to document that fact.

Do not promise absolute zero retention: transient processing and provider operational/billing metadata must be distinguished from stored request content. The precise retention period of provider metadata is unconfirmed. LEGAL-001 owns the final assessment and disclosures [S5, S6, S7].

| Data class | Proposed application policy | Known limitation |
|---|---|---|
| Real-user request/response diagnostic copies | Do not persist; do not put in logs/traces/artifacts | In-memory processing still exists |
| Owner-saved generated documents | Persist only by explicit save; same ownership/export/deletion boundaries | AI-001..005/PRIV integration still to implement |
| Usage ledger metadata | Opaque operation ID, owner relation, task/model alias, token counts, cost currency, outcome; 30-day technical default | Legal/accounting retention may require a revised policy before activation |
| General monitoring | Aggregates; request IDs and safe error category, no content or identities | Provider metadata lifetime not asserted |
| Synthetic golden evidence | Version-controlled sanitized fixtures and accepted summaries | Must never be mixed with user records |

The zero-day diagnostic policy does not delete user-saved resumes and is not a legal retention period. Usage owner relations must be removed/anonymized on account deletion subject to approved retention rules. No unsalted hashes of profile text as pseudo-anonymous telemetry.

## 3. Future credentials and kill switches

New production credentials must be separate from `AI_BENCH_*` GitHub secrets. Proposed names only: `AI_YANDEX_API_KEY`, `AI_YANDEX_FOLDER_ID`, `AI_YANDEX_MODEL_URI`. Use a dedicated service account, least-privilege language-model role and execution scope, expiry and a rotation runbook [S9, S10]. Never ask the user to paste values in chat or commit them to a ZIP.

Future runtime defaults: `AI_ENABLED=0`, `AI_KILL_SWITCH=1`. Both and the provider/market gates must be checked before dispatch. Emergency sequence: stop admission -> cancel queued/not-started work -> retain uncertain billing reservations -> revoke compromised provider key -> review safe logs -> requalify before re-enable. Already accepted upstream calls may still complete or be billed; a local kill switch cannot recall their data.

These environment names are not read by the current application. No Render environment change is required now. AI-001 must implement shared admission/kill-switch semantics for workers and replicas; an in-memory counter alone is insufficient.

## 4. Failure and retry policy

| Condition | Proposed handling |
|---|---|
| 429 / 502 / 503 / 504 | At most one retry, same qualified provider, bounded delay only within remaining deadline and reserved budget; honor Retry-After or stop if too long |
| Authentication / permissions / retired model / invalid request | No retry loop; safe configuration error; operator notification without credentials |
| Read timeout with unknown upstream outcome | No automatic resend; retain uncertain reservation; do not assume zero cost |
| Safety refusal / invalid schema / unsupported claims | No auto-repair of candidate facts, no cross-model retry to bypass rejection; keep editor usable |
| Cost ledger unavailable / cap exceeded / kill switch | No API dispatch; preserve user data and explain availability/limit state |
| Repeated eligible provider failures | Proposed breaker: three consecutive failures, 60-second pause, one half-open probe from real admitted work |

Proposed wall-clock limits: 25 seconds per attempt, at most two attempts, delay at most two seconds, whole operation at most 55 seconds. These are design choices, not measured SLA values. Connect/read timeouts alone do not guarantee a wall-clock deadline; AI-001 must enforce cancellation/deadlines across layers.

Manual fallback is mandatory when generation is unavailable. The user-facing UI must explicitly say that AI is temporarily unavailable and that manual functions remain available; it must never imply another model succeeded. Vacancy search, career profile and manual resume editing remain usable. A failed generation does not consume a future commercial entitlement, although uncertain provider cost remains reserved until reconciled. No automatic resume changes, job applications or employer messages.

## 5. Cost accounting and idempotency contract for AI-001

Compute input size including system instructions, schema, history, evidence and user input. When oversized, select relevant confirmed facts transparently or ask for narrower scope; do not silently drop a material job requirement. Reserve the maximum possible cost of all permitted attempts atomically against technical user/day, global/day and month caps. The stricter guard wins. Commercial plan entitlements are a separate check: AI-001 must read them from a central quota layer, while BILL-001 later supplies Free/Standard values. The provider adapter must not contain tariff numbers.

Use a durable request identifier plus owner/task/profile-version/vacancy-version/prompt-version context to prevent double-clicks and queue redeliveries from silently charging twice. Do not hold database locks during network I/O. Record dispatch/settlement state and each billable attempt. Unknown usage keeps its reservation until reconciled; negative or missing usage is not zero. The provider invoice remains authoritative. Usage rounding must never under-reserve the budget.

A model/prompt/schema change invalidates cached qualification. Recheck price snapshots before activation and after 30 days or a announced price change; a stale price disables dispatch in the future runtime. This candidate's offline tests use explicit dates, not fragile wall-clock assumptions.

## 6. Legal and deployment gates

LEGAL-001 must review purpose-specific consent, processing recipients/regions, user disclosures, provider mentions, account deletion/export and applicable RU/BY obligations. First-person cover letters are editable drafts, not a promise of human authorship in settings where AI use is prohibited [S5]. Public copy must not claim infallibility or guaranteed hiring outcomes.

Before public use: verify the owner's actual billing/eligibility and quota settings; confirm model URI and logging opt-out; test from the selected production IP; implement runtime controls and recovery; approve hosting/data flow and backup restoration. Healthy Neon staging does not satisfy those release gates.

## 7. Verification and rollback

Offline tests assert that unsafe policy settings are rejected, but do not prove provider-side deletion, legal compliance or deployed enforcement. No live operation was attempted. Revert this package without schema rollback; incident handling in production belongs to the future runtime implementation.

## 8. Next action and version log

Owner review and ordinary CI #262 are complete. Continue to LEGAL-001; no paid live benchmark or new secret is needed for this package.

| Version | Date | Change |
|---|---|---|
| 1.2 | 2026-09-14 | Approved manual fallback warning and activation boundaries; ordinary CI #262 green; package closed |
| 1.0 | 2026-09-14 | Proposed data, consent, secrets, failure, accounting and activation boundaries |
| 1.1 | 2026-09-14 | Owner-approved manual-mode warning and separation of technical cost guards from future commercial entitlements |
