# AI Career Agent - AI-PROVIDER-001 / Provider decision record

| Поле | Значение |
|---|---|
| Document | AI_PROVIDER001_DECISION |
| Package | AI-PROVIDER-001 |
| Version | 1.0 |
| Date | 2026-09-14 |
| Status | НУЖНА ПРОВЕРКА; owner decision and external CI pending |
| Scope | Architecture and offline validation only; no production AI activation |
| Schema revision | 20260819_0014 (unchanged) |

## 1. Decision proposed for owner approval

Use **Yandex AI Studio / Alice AI LLM** as the first production integration candidate for the four evaluated tasks in Russian and English. Treat this as an approved-model shortlist of one, not as an always-available or universally accurate service. Until LEGAL-001 and AI-001 are complete, public AI traffic stays off.

The reserve mode is **manual work without generation**, not an automatic switch to an unqualified model. Search, profile editing and resume editing must remain available when AI is unavailable. Do not present keyword heuristics or a static template as a successful AI response.

This ADR is a candidate, not a recorded owner acceptance. The existing acceptance by reviewer Shekunov D.S. closes AI-BENCH-001 only. It does not approve the new budgets, contractual interpretation or production activation in this document.

## 2. Evidence and alternatives

The accepted artifact `34830877796` / run `ai-bench-20260914T100639Z-222dfc87` has eight passing synthetic RU/EN cases, zero API errors/retries and zero unresolved hard counters. Audited normalization remains visible: two scenario-provenance repairs and fourteen known-marker cleanups. The owner accepted writing quality separately. See `docs/evidence/ai-bench-001/alice-final-run-7-summary.json` and the named human review.

Eight sparse cases establish a useful baseline, not robustness on every real CV, a production SLA or a universal absence of hallucinations. Rich-input, adversarial, load and production UI tests remain gates of AI-001..006. The English letter is short partly because the prompt deliberately restricts claims; extra source facts may help, but the benchmark did not prove automatic adaptation to rich profiles.

| Option | Current evidence | Decision |
|---|---|---|
| Alice AI LLM | Current dataset 1.3.6 / grounded-v2.6.1 accepted | Primary integration target, activation blocked |
| Alice Flash | Older comparative run, not qualified on current contract | No automatic fallback; future evaluation only |
| YandexGPT Pro 5.1 | Older comparative run, not qualified on current contract | No automatic fallback; future evaluation only |
| Local/open-weight model | No approved model, license audit, hardware or current benchmark | Deferred; do not assume a CPU VPS is sufficient |
| Other external API | No current project qualification or market/privacy decision | Disabled, no cross-provider data transfer |

OpenAI is not a mandatory RU/BY baseline, as already decided in the project. This package does not create a new claim about every other vendor's current eligibility. No more model-shopping or paid benchmark is needed to review this ADR.

## 3. Geography, commercial use and service conditions

Public contractual and billing sources were checked on 2026-09-14; details and URLs are in `AI_PROVIDER001_SOURCES.md`. Product integration is the chosen model, not API resale [S5]. Planned markets are RU and BY; both use the same qualified Alice route. English language is not a reason to send data to a different vendor or legal region.

Public payment routes for RU/BY exist [S8], but the owner's tax residency, billing account status, limits and production-source-IP connectivity were not verified. These remain activation checklist items. A past successful synthetic call from GitHub is evidence of that route at that time, not a guarantee for a future VPS or every user network.

Render web + Neon Oregon remains a temporary development/staging topology confirmed in the prior chat. No production data-locality conclusion is drawn from its healthy PostgreSQL status. Real personal-data AI use on that topology is not approved by this ADR. LEGAL-001 must map the whole data flow and hosting region; INFRA-001 retains the future production-IP check. The old Render DB contents were not migrated.

## 4. Routing and output contract

| Task | Language | Planned provider | Required product boundary |
|---|---|---|---|
| resume_analysis | ru / en | Alice AI LLM | Grounded findings; suggestions are not confirmed facts |
| vacancy_match | ru / en | Alice AI LLM | Evidence-based requirement assessment; numeric score computed by code |
| cover_letter | ru / en | Alice AI LLM | First person; only verified relevant facts; caveats excluded from letter |
| interview_questions | ru / en | Alice AI LLM | Explicit hypothetical scenarios; no invented candidate history |

The machine-readable architecture specification is `docs/policies/ai_provider_policy.v1.json`. Unknown tasks, languages or markets are denied. All enabled-market lists are empty now; a route preview never authorizes an API call.

For AI-001, the transport target is synchronous JSON-schema output over the endpoint already exercised by the benchmark. The exact deployment model URI must be stored in a server secret/config store and recorded without credential values. `aliceai-llm/latest` is observed metadata, not an immutable version proof. Changing provider/model, major prompts or safety semantics requires a fresh qualified evaluation and an explicit decision [S2].

Production must use a new `services/ai/` boundary, not import the benchmark adapter directly. Separate authentication, normalization, schema validation, semantic grounding and presentation from route handlers. Retain raw/machine/presentation separation only for synthetic evaluation; do not enable real-user prompt dumps for debugging. A rejected answer is not silently rewritten or treated as success.

## 5. Privacy, failure handling and limits

`AI_PROVIDER001_DATA_AND_FAILURE_POLICY.md` specifies data minimization, opt-out prerequisites, future secrets and failure semantics. In particular, the accepted synthetic adapter lacks the proposed production no-logging header; copying it into the live application would be insufficient.

`AI_PROVIDER001_COSTS.md` separates observed usage, published prices and proposed caps. The proposed caps are not active software limits and do not authorize a payment. Runtime admission, token estimation, atomic reservations, billing reconciliation and kill switches still need implementation and tests in AI-001.

No automatic fallback is allowed after provider refusal, grounding failure or missing permissions. Such failures cannot be solved by quietly sending a user's profile to another model. The user's editable data must remain intact.

## 6. Implementation and application impact

This package adds an offline policy validator, deterministic Decimal cost report, negative tests, a dedicated CI verification step, source audit and canonical documentation. It synchronizes the final AI-BENCH closure into repository docs and corrects stale active schema/status rows explicitly listed in SOURCE_AUDIT.

The preserved-file check is scoped to this candidate; AI-001 must deliberately revise that check when runtime implementation is approved, rather than silently bypassing it.

No routes, production services, SQLAlchemy models, migrations, dependencies, templates, static resources, Render variables or benchmark prompts are changed. Database revision stays `20260819_0014`. The preserved-file manifest verifies this boundary. The website will not gain AI buttons or new charges from this package.

## 7. Verification, limitations and rollback

Local results are recorded in `AI_PROVIDER001_VERIFICATION_STATUS.md`. New external GitHub CI and owner approval have not yet occurred. No credentials, real-user input or billable APIs were used to produce these deliverables.

Rollback is reverting this package's documents, policy and validation scripts/CI step. No database rollback is required. Later incident handling must use runtime controls from AI-001, not edits to this offline JSON.

## 8. Approval and next action

Approve or revise: Alice as primary; no generative fallback until qualification; privacy gates; proposed caps; no real-user activation before legal/runtime/infrastructure requirements. After ordinary CI and owner approval, AI-PROVIDER-001 can be closed and **LEGAL-001** becomes next. AI-001 is not started in this package.

## 9. Version log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-14 | Candidate strategy; current sources, cost model, closed offline policy and CI checks; approval pending |
