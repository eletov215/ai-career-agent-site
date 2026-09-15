# AI Career Agent - AI-PROVIDER-001 / Provider decision

| Поле | Значение |
|---|---|
| Document | AI_PROVIDER001_DECISION |
| Package | AI-PROVIDER-001 |
| Version | 1.2 |
| Date | 2026-09-14 |
| Status | УТВЕРЖДЕНО ВЛАДЕЛЬЦЕМ; ordinary GitHub CI #262 green; package complete |
| Owner approval | Шекунов Д.С., 2026-09-14 |
| Scope | Architecture and offline validation only; no production AI activation |
| Schema revision | 20260819_0014 (unchanged) |

## 1. Decision

The primary provider for the planned RU/EN AI functions is **Yandex Alice AI LLM**, qualified by AI-BENCH-001 on grounded-v2.6.1. Unknown routes remain denied. No unqualified provider, local model or cross-provider automatic fallback is enabled.

If Alice is unavailable, the product falls back to **manual mode without generation**. The user must receive an explicit notice that AI is temporarily unavailable; vacancy search, career profile and manual resume editing remain available. The interface must not pretend another model succeeded. A failed generation must not consume a future user-visible commercial entitlement, although provider-side cost reservations may still need settlement when upstream usage is uncertain.

## 2. Cost guard versus commercial tariff

Two different limit layers are mandatory and must not be mixed:

1. **Technical safety guards** protect the service from loops, abuse and unexpected provider spend. Initial beta planning values are 100 logical AI requests per user/day, 1000 globally/day, RUB 200 per user/day, RUB 1000 globally/day and RUB 20000 globally/month. These are operator safety ceilings, not a customer plan, not a price and not permission to spend.
2. **Commercial entitlements** define what Free/Standard/Max customers receive. Exact action quotas are intentionally unset in AI-PROVIDER-001. AI-001 must create a central quota architecture; BILL-001 later assigns commercial values from observed usage and unit economics.

The provider adapter must never contain tariff numbers. Limits must be read from a central server-side quota policy so they can be changed without rewriting provider integration.

## 3. Commercial access strategy

The launch intent is **Free + Standard**. A third **Max** tier is reserved in the architecture but not launched until real usage demonstrates a distinct heavy-user segment.

- **Free** must deliver one complete small value loop (for example, experience enough AI analysis/match/letter capability to understand the product) but must not satisfy an active job seeker's recurring needs indefinitely.
- **Standard** is the main paid tier and should support normal active job search without micro-metering every token.
- **Max** remains architecture-ready for heavy usage or additional premium capabilities after demand and unit economics are observed.
- Users should see feature actions/allowances, not raw token counts. Tokens and RUB remain internal accounting dimensions.

Exact monthly Free/Standard allowances, subscription price, payment provider, upgrades/downgrades and paid overage belong to BILL-001. Nothing in this package activates billing.

## 4. Planning workload and headroom

The owner scenario used for planning is: three resumes, one generation plus one refinement each; 10 AI-reviewed shortlisted vacancies per resume; 4-5 cover letters per resume. Under the explicit token assumptions in `AI_PROVIDER001_COSTS.md`, the estimated provider cost is RUB 85.92-92.04, or RUB 103.104-110.448 with a 20% operational buffer. The RUB 200 per-user daily technical guard therefore has headroom for this scenario but is not a future Standard-plan quota.

## 5. Routing and output contract

| Task | Language | Planned provider | Product boundary |
|---|---|---|---|
| resume_analysis | ru / en | Alice AI LLM | Grounded findings; suggestions are not confirmed facts |
| vacancy_match | ru / en | Alice AI LLM | Evidence-based requirements; numeric score computed by code |
| cover_letter | ru / en | Alice AI LLM | First person; only verified relevant facts; caveats excluded from the letter |
| interview_questions | ru / en | Alice AI LLM | Explicit hypothetical scenarios; no invented candidate history |

The machine-readable specification is `docs/policies/ai_provider_policy.v1.json`. All enabled-market lists remain empty; this package cannot authorize an API call.

## 6. Privacy and activation boundary

Real personal data remains blocked until LEGAL-001 and AI-001 complete their gates. Production requests must use the documented no-logging control, confirm the account/provider opt-out procedure and wait at least 24 hours after the required disablement action before real personal-data requests. Minimize payloads to confirmed relevant profile facts and bounded vacancy facts; never log prompt/response bodies.

The exact production model URI, billing account/quota state, production source-IP transport and data-location/backup decision must be verified before activation. Render + Neon remains development/staging only.

## 7. Runtime architecture reserved for AI-001

AI-001 must implement a provider-neutral `services/ai/` boundary, structured schemas, versioned prompts, durable usage accounting, atomic cost reservations, idempotency, central quota/entitlement lookup, kill switch, deadline/retry policy and user-facing availability/limit states. The quota layer must be independent from Alice so Free/Standard/Max values can change without provider rewrites.

No production route, SQLAlchemy model, migration, template, Render secret or provider call is added by AI-PROVIDER-001.

## 8. Verification and next action

Candidate r1 ordinary GitHub CI is green. Owner approval is now explicit. Because this revision changes the policy contract/tests/docs, ordinary GitHub CI run #262 is green; AI-PROVIDER-001 is `ВЫПОЛНЕНО`. Paid Alice benchmark repetition is not required because prompts/evals/provider qualification are unchanged.

AI-PROVIDER-001 is closed. Continue with **LEGAL-001**. AI-001 follows the legal gate.

## 9. Version log

| Version | Date | Change |
|---|---|---|
| 1.2 | 2026-09-14 | Owner approval + ordinary CI #262 green; package closed; LEGAL-001 next |
| 1.0 | 2026-09-14 | Candidate strategy and offline controls; approval pending |
| 1.1 | 2026-09-14 | Owner-approved fallback warning, technical-vs-commercial split, Free+Standard launch intent, Max reserved, configurable quota architecture |
