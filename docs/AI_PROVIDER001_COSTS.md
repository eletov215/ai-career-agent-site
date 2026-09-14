# AI Career Agent - AI-PROVIDER-001 / Cost and quota model

| Поле | Значение |
|---|---|
| Document | AI_PROVIDER001_COSTS |
| Package | AI-PROVIDER-001 |
| Version | 1.1 |
| Date | 2026-09-14 |
| Status | Owner-approved model; final ordinary CI pending |
| Scope | Planning and offline validation only; no billing or production AI activation |
| Schema revision | 20260819_0014 (unchanged) |

## 1. Price basis

Price snapshot checked on 2026-09-14 [S1]: synchronous Alice input RUB 0.5 / output RUB 1.2 per 1000 tokens, VAT included. Formula: `cost = (input_tokens * input_rate + output_tokens * output_rate) / 1000`. The provider invoice remains authoritative.

The accepted eight-case benchmark reprices to **5120 input + 3560 output tokens = RUB 6.832**. This is synthetic evidence, not a production workload average.

## 2. Planning examples

| Input / output tokens | One attempt, RUB | Two-attempt reserve, RUB |
|---|---:|---:|
| 1000 / 300 | 0.86 | 1.72 |
| 4000 / 700 | 2.84 | 5.68 |
| 8000 / 1600 | 5.92 | 11.84 |

These examples exclude hosting, database, payment processing and future storage.

## 3. Owner heavy-use scenario

Planning assumptions (not measured averages):

- 3 resumes;
- 2 AI calls per resume (initial + one refinement), each assumed 4000 input / 1200 output tokens;
- 10 AI-reviewed shortlisted vacancies per resume = 30 match calls, each 2000 / 300 tokens;
- 4-5 cover letters per resume = 12-15 letters, each 3000 / 450 tokens.

| Component | Estimated RUB |
|---|---:|
| 6 resume calls | 20.64 |
| 30 vacancy-match calls | 40.80 |
| 12-15 cover letters | 24.48-30.60 |
| **Base total** | **85.92-92.04** |
| **With 20% operational buffer** | **103.104-110.448** |

The buffer covers longer payloads, bounded retries and variance. It is not a forecast of average customer cost.

## 4. Approved technical safety guards

| Control | Initial beta guard | Meaning |
|---|---:|---|
| User logical requests | 100/day | Anti-loop/abuse guard; not a tariff quota |
| Global logical requests | 1000/day | Service safety guard; operator-adjustable |
| User provider-cost ceiling | RUB 200/day | Emergency spend ceiling; hidden from commercial packaging |
| Global provider-cost ceiling | RUB 1000/day | Initial beta service ceiling |
| Global provider-cost ceiling | RUB 20000/month | Initial beta monthly ceiling |
| Concurrent calls | 2 global / 1 per user | Technical concurrency bound |
| Attempts | max 2 | Only eligible transient failures |
| Input/output | 8000 / 1600 tokens | Planning payload ceiling |

These values must live in a central server-side quota policy, not inside the Alice adapter. They can be adjusted as active-user count changes. A future admin control may edit them; AI-001 must at minimum make them centralized and testable.

## 5. Commercial tiers are deliberately not priced here

Commercial access is separate from technical guards:

- launch intent: **Free + Standard**;
- **Max** is architecture-reserved, not launched;
- exact Free/Standard monthly action quotas are `unset` until usage data exists;
- user-facing limits should be expressed as actions (analysis, match, letters, interviews), not tokens;
- BILL-001 owns subscription price, payment provider and commercial quota values.

Free should demonstrate a complete small value loop while preserving a reason to upgrade. Standard should cover normal active job search without constant token accounting. Max is introduced only if real demand justifies it.

## 6. Accounting contract for AI-001

AI-001 must record operation/task, input/output tokens, provider/model alias, estimated/reserved/settled cost and outcome. Reserve the maximum allowed cost atomically before dispatch; settle from returned usage; keep uncertain reservation when the upstream outcome is unknown. A failed generation should not consume a user's future commercial entitlement, even if provider-side spend must still be reconciled.

The stricter technical cap wins. Commercial entitlements are checked separately and must not be encoded in the provider adapter.

## 7. Reproduction

```bash
python scripts/ai_provider_policy.py --cost-report
python scripts/check_ai_provider_package.py
python -m unittest discover -s tests -p 'test_ai_provider*.py' -v
```

`docs/evidence/ai-provider-001/cost_snapshot.json` is reproducible from the policy and accepted benchmark summary.

## 8. Version log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-14 | Candidate cost model and conservative proposal |
| 1.1 | 2026-09-14 | Owner scenario, RUB 200 technical user guard, central mutable limits, Free+Standard/Max separation |
