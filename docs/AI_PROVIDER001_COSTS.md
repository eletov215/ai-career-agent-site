# AI Career Agent - AI-PROVIDER-001 / Cost and quota model

| Поле | Значение |
|---|---|
| Document | AI_PROVIDER001_COSTS |
| Package | AI-PROVIDER-001 |
| Version | 1.0 |
| Date | 2026-09-14 |
| Status | НУЖНА ПРОВЕРКА; owner decision and external CI pending |
| Scope | Architecture and offline validation only; no production AI activation |
| Schema revision | 20260819_0014 (unchanged) |

## 1. Price basis and scope

Prices checked on 2026-09-14 [S1]: synchronous Alice input RUB 0.5 / output RUB 1.2 per 1000 tokens, including VAT. Separate USD tariffs exclude VAT. This report does not convert currencies. No cache discount, grant, tool call or asynchronous discount is assumed.

Formula: `cost = (input_tokens * input_rate + output_tokens * output_rate) / 1000`.
`reserve = maximum_per_attempt_cost * permitted_attempts`.

Calculations use `Decimal`, not binary floating-point. API usage fields from the accepted synthetic artifact are the empirical input; the prices are a dated external snapshot. This is neither an invoice nor a representative commercial workload forecast.

## 2. Repriced accepted synthetic run

| Case | Input tokens | Output tokens | RUB incl. VAT |
|---|---|---|---|
| resume-analysis-ru-01 | 346 | 532 | 0.8114 |
| resume-analysis-en-01 | 257 | 501 | 0.7297 |
| vacancy-match-ru-01 | 444 | 312 | 0.5964 |
| vacancy-match-en-01 | 422 | 280 | 0.547 |
| cover-letter-ru-01 | 922 | 190 | 0.689 |
| cover-letter-en-01 | 1285 | 211 | 0.8957 |
| interview-ru-01 | 740 | 738 | 1.2556 |
| interview-en-01 | 704 | 796 | 1.3072 |

Total: **5120 input + 3560 output tokens; RUB 6.832** for eight cases at the checked RUB tariff. The same counts evaluated using the USD tariff give approximately USD 0.056 excluding VAT, consistent with the artifact's rounded USD 0.055999992. These are two tariff-based calculations, not a currency exchange.

Mean repriced synthetic cost by task (two languages each): resume analysis RUB 0.77055; vacancy match RUB 0.57170; cover letter RUB 0.79235; interview questions RUB 1.28140. Two examples per task cannot establish a production mean.

## 3. Planning scenarios, not measured requests

| Assumption | Input / output | One attempt, RUB | Two-attempt reserve, RUB | 1000 one-attempt jobs, RUB |
|---|---|---|---|---|
| Sparse profile illustration | 1000 / 300 | 0.86 | 1.72 | 860 |
| Richer profile illustration | 4000 / 700 | 2.84 | 5.68 | 2840 |
| Proposed token ceilings | 8000 / 1600 | 5.92 | 11.84 | 5920 |

These values exclude hosting, PostgreSQL, future file storage, taxes not covered by the chosen tariff and other product costs. Output length is not forced to reach the ceiling; richer input does not guarantee useful longer prose. A billable retry or a larger system prompt increases usage.

The 1600-output-token cap matches the accepted benchmark configuration. The 8000-input cap and workload examples are new proposals, not existing production behavior. Changes require review and appropriate evaluation.

## 4. Proposed conservative development caps

| Control | Proposal | Status |
|---|---|---|
| Concurrent provider calls | 2 globally, 1 per user | Not runtime-enforced yet |
| Attempts per logical request | At most 2, only eligible errors | Not a success guarantee |
| User request count | 10 per UTC day | Budget cap can stop earlier |
| Global request count | 100 per UTC day | Budget cap can stop earlier |
| User budget | RUB 20 per UTC day | Proposal, not a tariff to charge users |
| Global budget | RUB 100 per UTC day, RUB 1000 per UTC calendar month | Proposal, not permission to spend |
| Input / output caps | 8000 / 1600 tokens | Full payload must be counted |

At maximum reservation (RUB 11.84), a user budget of RUB 20 permits only one simultaneously reserved maximum-cost operation until settlement. Daily monetary caps are not automatically multiplied into a payment authorization. The monthly cap wins even if daily limits remain available.

The provider's documented concurrency quota [S3] is not the application's own budget or rate limit. Actual account quotas must be checked before enabling calls. Cloud budget alerts are not assumed to be hard cost cut-offs.

## 5. Reproduction and verification

Run offline from the repository root:

```bash
python scripts/ai_provider_policy.py
python scripts/ai_provider_policy.py --cost-report
python scripts/check_ai_provider_package.py
python -m unittest discover -s tests -p 'test_ai_provider*.py' -v
```

`docs/evidence/ai-provider-001/cost_snapshot.json` is reproducible from the checked policy and immutable accepted summary. The checker fails when recorded costs drift. No secrets, API calls or production records are used.

## 6. Rollback, next action and version log

Reverting the offline report has no billing effect. Actual budget enforcement is an AI-001 deliverable. Owner approval is needed for the proposed caps; commercial pricing and subscriptions remain BILL-001, not this package.

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-14 | Source-priced cost model and conservative proposal; no live spending authorized |
