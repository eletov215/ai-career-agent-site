# AI Career Agent - AI-002 / Rebuilt implementation

## 0. Accepted status / 2026-09-15

AI-002: **ВЫПОЛНЕНО** in synthetic/reference-only scope. Final owner-supplied documents dated 2026-09-15 establish CI #270 PASS after the import hotfix, Neon staging at `20260915_0016`, owner review/relogin persistence and the final conditional-actions UI smoke. `AI_ANALYSIS_REVIEW_ENABLED` was returned to disabled; `/api/ai/status` remained manual/unavailable. No new paid Alice call and no real resume dispatch were required. A post-UI-hotfix CI run number is not known; the current main (33) archive comment is recorded as source evidence, not a new CI claim.

The detailed reconstruction instructions below are historical AI-002 procedures. Current deployment target and review steps are in AI003_RUNBOOK; do not downgrade the current candidate to 0016 as an ordinary deployment step.


| Field | Value |
|---|---|
| Version | 1.0-r2 / 2026-09-15 |
| Package | AI-002 v1.5.2; NEEDS_VERIFICATION |
| Baseline | main (32).zip / bc177dd |
| Boundary | Synthetic-only; public AI and payments disabled |

## 1. Delivered scope

The lost candidate was NOT recovered byte-for-byte. This is a new, measured rebuild. The feature accepts only resume-analysis-ru-01 or resume-analysis-en-01 pinned by AI-001. It stores a versioned report, immutable source facts, source/prompt hash, language, explicit reference/provider origin and separate recommendation decisions/events. It never writes career_profiles or resume_drafts.

Internal provider calls reuse AI-001. Feature validation runs after JSON Schema validation and before settlement, so a rejected semantic result does not consume a successful future commercial action. Upstream usage still costs money. Strict fixed-fixture checks cover known evidence IDs, missing/unverified disclosures, unsupported numbers/impact and presentation leakage. These are not a universal semantic truth proof for arbitrary resumes.

## 2. Reference review vs live generation

/ai-analysis is disabled by default. AI_ANALYSIS_REVIEW_ENABLED=1 plus an active verified SEARCH_ADMIN_EMAILS allowlisted account permits a reference-only UI. Its POST /reference accepts only fixture ID, source hash, idempotency key and CSRF. No arbitrary text, upload, JSON body or extra fields are accepted. It copies pinned developer-authored reference outputs, explicitly labeled as references, without calling Alice. Runtime controls stay off.

The internal analyze method is tested with a fake provider. It can only dispatch real synthetic calls through all existing AI-001 gates, with a separate future authorization. This rebuild does not add a browser live-generation endpoint, use real profile data, or implement consent.

## 3. Storage, ownership and review

0016 adds resume_analysis_reports, resume_analysis_decisions and resume_analysis_review_events. Writes lock the owner row (SQLite BEGIN IMMEDIATE); no network executes under those locks. Same operation keys are idempotent per owner; cross-fixture/source/origin collisions are rejected. Every material review change has a monotonically increasing revision and history event. Stale conflicting decisions fail with 409; identical repeated transitions are no-ops. Reports do not become confirmed profile facts.

Owner export includes saved reports/decisions/events, excluding HMAC operation keys. Account deletion cascades report data. Explicit report deletion is also available in the private UI. History is capped at 100 saved reports per owner. Linked ledger metadata may expire independently. Missing content after an interrupted provider-to-report save is NOT regenerated and billed again silently.

## 4. Limitations and acceptance

Real-PDF/profile analysis, production grounding at arbitrary input size, calibrated confidence scores, provider-driven new prompts and public activation remain outside this closed candidate. Evidence links express source linkage, not a made-up accuracy percentage. No new billable call was made. Run ordinary CI, migration/readiness and private reference-review smoke before closing AI-002. See AI002_VERIFICATION_STATUS.md and AI002_RUNBOOK.md.
