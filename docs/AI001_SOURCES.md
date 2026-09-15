# AI Career Agent - AI-001 / Sources and assumptions

| Поле | Значение |
|---|---|
| Document | AI001_SOURCES |
| Version | 1.2 |
| Date | 2026-09-15 |
| Package | AI-001 |
| Status | AI-001 ВЫПОЛНЕНО; public AI disabled |
| Verified schema | 20260914_0015 on staging |

## 1. Project evidence

Owner-supplied main(31) ZIP is the code baseline. Separate canonical PLAN1.4.51/PASSPORT2.65 establish accepted AI-PROVIDER closure. The owner now explicitly postpones unresolved legal choices and asks to continue technical work. No operator identity, launch country or paid-call authorization is inferred.

Accepted benchmark prompts/schemas come from grounded-v2.6.1, dataset1.3.6. The historical8/8 report is provider qualification, not evidence that this new transport ran live. Full input/change evidence is in SOURCE_AUDIT and docs/evidence/ai-001.

## 2. Primary technical sources checked 2026-09-14

| Source | Reference | Use / limitation |
|---|---|---|
| Yandex AI Studio no logging | https://aistudio.yandex.ru/docs/en/ai-studio/operations/disable-logging.html | x-data-logging-enabled:false; runtime header is not evidence of account opt-out |
| Yandex structured completion | https://aistudio.yandex.ru/docs/ru/ai-studio/operations/generation/completions-structured.html | Chat-completions schema format and project/API-key headers |
| PostgreSQL17 explicit locking | https://www.postgresql.org/docs/17/explicit-locking.html | Transactional row lock for singleton admission |
| Requests timeout semantics | https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts | Socket timeout alone is not a total response deadline |

## 3. Approved policy, not new external facts

The24-hour no-logging wait and dated rate snapshot are carried from the approved AI-PROVIDER policy. Actual billing account, no-logging action and production network reachability are unverified. Daily/monthly caps are technical limits, not payment permission.

Legal deferral records an owner decision; this release provides no new country-specific legal advice or assertion of compliance. The final jurisdiction, operator, data placement and consent wording require future LEGAL-001 work.

## 4. Engineering assumptions

The beta uses one central policy row to serialize admissions. This favors predictable safety over high throughput. Input length is estimated on immutable synthetic fixtures, not tokenized by the provider. Unknown costs are retained and not represented as an exact invoice. JSON Schema validity does not imply full semantic factuality.

## 5. Version log

1.1 / 2026-09-14: dated sources and explicit distinction between measured evidence, policy and assumptions.


## 6. External acceptance evidence / 2026-09-15

The owner supplied GitHub CI #266 and live Render endpoint screenshots. They support only the claims recorded in AI001_VERIFICATION_STATUS v1.2: CI success, staging revision `20260914_0015`, manual runtime state and normal vacancy/core smoke. They do not provide a file-by-file copy of current GitHub `main`; a fresh ZIP is still required before AI-002 changes.

## 7. Version log update

1.2 / 2026-09-15: external CI/staging evidence added; source-archive gap explicitly recorded.
