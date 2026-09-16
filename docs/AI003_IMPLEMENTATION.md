# AI Career Agent - AI-003 adaptive interview foundation

| Поле | Значение |
|---|---|
| Version | 1.1 FINAL / 2026-09-16 |
| Status | ВЫПОЛНЕНО / PASS in synthetic/reference-only scope |
| Accepted lineage | owner `ai-career-agent-site-main-2.zip` + r1.2 session-review hotfix |
| Target schema | 20260916_0017 |
| Feature mode | synthetic/reference-only; no live provider |

## 1. Delivered technical scope

A private interview associated with the resume builder, driven by two pinned RU/EN reference fixtures. These are new interview fixtures, not modifications to the accepted Alice benchmark. Only known choice IDs can be submitted. No free text, upload, existing resume ID or canonical profile is accepted as interview input.

The state machine is bounded and adaptive: an imprecise answer asks for a concrete contribution; a numeric outcome asks for period/source; an uncertain number routes to a nonnumeric description. A skip contributes no facts. A rewind discards later answers from the active path but retains their audit events. Questions, goals and metric hints are stored with the source snapshot. There is no model-generated prose or hidden fallback.

## 2. User control and builder integration

Starting an interview creates a new isolated synthetic `ResumeDraft` with a test label and source seed. The ordinary builder has one conditional private-review link; its editing, image, preview and PDF implementation is preserved. The interview page presents conversation, goals/hints, original test facts, provisional statements and history. Users may unselect suggested facts and must explicitly confirm before a write to the draft.

A final statement must be an exact selected reference-answer fact. A bare number is not added; period/source confirmation supplies the complete metric fact. No unknown skill/result/impact is inferred. Confirmation updates only `answers.achievements` in that test draft and creates an immutable PROF-003 `ResumeVersion` atomically with the interview event. It does not modify `career_profiles`. Normal manual editing remains available afterward. Final free-form review and live semantic rewriting are not implemented by r1.

## 3. Persistence and consistency

Migration `20260916_0017` adds `resume_interview_sessions` and `resume_interview_events`, with owner/draft FKs, unique start/operation identifiers and per-session revisions. No existing table/row is rewritten by the migration. Each session stores the immutable reference snapshot/hash/version, language/origin, active answer path, original draft revision/hash, lifecycle state and final version reference.

PostgreSQL locks owner and draft rows; SQLite test writes use `BEGIN IMMEDIATE`. Duplicate operations replay current state without duplicate events/versions. Conflicting keys return a controlled conflict. Expected interview revision and source hash prevent stale writes. Confirm also checks the draft's original revision/hash: a simultaneous manual edit must not be overwritten. Final draft/version/session/event writes share one transaction. An error rolls all of them back.

Bounds: two fixtures, no more than eight graph steps, 50 sessions per owner, 60 events per session, 12 selected facts and 16 KiB API command bodies. Session cap is released by deleting a test draft. A full history-cap session remains readable but requires a new session for further changes.

## 4. Access and API

`AI_INTERVIEW_REVIEW_ENABLED` defaults to false in application code and remains an optional operator-wide staging override. r1.2 also adds a safer per-browser review gate at `/ai-interview/review`: only an active, verified first-party administrator present in `SEARCH_ADMIN_EMAILS` can see it, and enabling review stores a single boolean in the signed Flask session. All other interview routes require the same administrator plus either the environment override or this current-session unlock. Logout/session rotation clears the unlock. Public/default/non-admin access receives 404; ordinary builder remains available. Global CSRF protects the enable/disable POSTs, per-route limits remain active, and interview responses keep no-store/noindex protection. SQL errors produce neutral 503 without parameters. Duplicate JSON/form fields and unknown fields are rejected.

| Method | Route | Purpose |
|---|---|---|
| GET | `/ai-interview/review` | Admin-only per-session review gate |
| POST | `/ai-interview/review/enable` | Unlock synthetic review in the current signed session |
| POST | `/ai-interview/review/disable` | Remove the current-session unlock |
| GET | `/ai-interview` | Private examples and owned sessions |
| POST | `/ai-interview/start` | Start a new synthetic draft/session |
| GET | `/resume-builder/<draft_id>/interview` | Private adaptive builder page |
| POST | `/ai-interview/<session_id>/actions` | Answer, rewind, confirm forms |
| GET | `/api/resume-interviews/<session_id>` | Owner-only state/history |
| POST | `/api/resume-interviews/<session_id>/actions` | Strict ID-only command API |

The new service/routes import no provider service. AI usage/cost ledgers are not touched. `REAL_DATA_SUPPORTED=False` and all public activation defaults remain unchanged.

## 5. Privacy and operations

Account export includes readable `resume_interviews` with history; operation/idempotency hashes are not exported. Owner checks fail closed on inconsistent data. Account or draft deletion cascades interview sessions/events through FKs. Backup inventory includes both new tables. No new logging of answers, database parameters, credentials or provider payloads is introduced.

The source manifest verifies fixture/schema bytes and the registry also validates graph termination, exact evidence text and allowed transitions. Historical AI-001/002 and provider preservation gates are extended by an explicit thirteen-file successor map; prior evidence manifests remain unchanged.

## 6. Compatibility and rollback

0017 is additive but application readiness enforces an exact migration head. An old application cannot be assumed ready on 0017. Before rollback: stop writers, verify backup, preserve any desired interview history, run a controlled downgrade to 0016 using the current migration code, then deploy the previous application. Downgrade removes the two interview tables and their history; it preserves synthetic resume drafts and existing PROF-003 versions. Do not erase the database/cache or remove DATABASE_URL.

## 7. Limits and accepted boundary

This foundation demonstrates deterministic branching, persistence and explicit confirmation. It does not provide a free-form live Alice interview, calibrated confidence, arbitrary real-resume generation or a public feature. Those remain outside the accepted AI-003 scope and require separate technical validation plus the unresolved legal/activation gates. See AI003_VERIFICATION_STATUS and AI003_RUNBOOK.

## 8. Final acceptance

Owner staging acceptance on 2026-09-16 passed after r1.2. Render/Neon is on `20260916_0017`, public AI remains disabled/manual, RU and EN reference flows passed, relogin/history, rewind, unsupported-number exclusion, explicit selection/confirmation, same-session stale-write protection, manual-builder conflict protection, privacy export/deletion integration, core regressions and final closed-access/log review were confirmed. A fresh two-account manual isolation run was not separately evidenced; automated ownership checks remain the accepted evidence for that subcase.

AI-003 is therefore **ВЫПОЛНЕНО** only within the documented synthetic/reference-only boundary. Arbitrary free text and live multi-turn Alice remain outside this package.
