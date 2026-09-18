# AI-005 implementation / 1.0 r1

Status: NEEDS_VERIFICATION for the document-workflow delivery. The entire planned AI-005 is IN_PROGRESS; live generation is not integrated. See AI005_SCOPE.md.

## 1. Ownership and sources

CoverLetter is bound to an active verified first-party user and their SavedVacancy by a composite foreign key. Explicit creation freezes the vacancy content/hash and selected allowlisted fields from the immutable current confirmed career-profile version. Structured contact fields, salary/geography preferences, saved notes, resume drafts and synthetic match reports are not candidate evidence. Empty profiles allow manual letters; no facts are invented. The source includes its version/hash, per-fragment IDs and omitted-field notice. Profile confirmation establishes a user declaration, not independent employment verification.

Creation uses a server-source preview hash and HMAC operation key. Duplicate requests while the object exists return it; changing parameters under the same key fails. Later profile changes mark the source stale rather than rewriting history. Local proposal creation/acceptance then requires a new letter; manual editing of the historical document remains available with a warning.

## 2. Editor, proposals, history and export

All saves are explicit native forms with review confirmation and expected_revision. A successful material save creates an immutable numbered version. An unchanged save does not consume a revision or version. Stale tabs fail409 and show both saved and unsaved text, escaped, without auto-resubmission against a fresh revision. Pending local proposals never replace current content automatically. Accepted proposals are removed after their content/provenance is recorded in a reviewed version; discarded proposal text is deleted. A changed proposal is labelled user_edited_local_template, not certified AI text.

The current version cannot be separately deleted; historical deletion increments the editor revision and does not reuse version numbers. Whole-letter deletion requires confirmation and removes its versions/proposals, not the vacancy/profile. TXT export is an authenticated download of one immutable reviewed version; it never exports an unreviewed proposal as a final letter. Comparison uses escaped unified text differences including preferences. No mail, clipboard auto-send, provider apply or notification is triggered.

## 3. Limits and concurrency

100 letters per owner;50 reviewed versions and20 pending proposals per letter;240 subject characters,8000 body characters; bounded source size and100 fact fragments. Short composition uses1-3 fragments, full1-8. Excerpts are copied without translation or numeric inference; tone changes framing only. Under PostgreSQL, short writes acquire the same owner row lock as JOB-001 with a5-second timeout; SQLite uses BEGIN IMMEDIATE. There is no network I/O under those locks. Both linked deletion and letter creation use this lock, preventing a check/delete race.

## 4. Migration and privacy

Migration0020 creates cover_letters, cover_letter_versions, cover_letter_proposals after0019. Composite ownership constraints and cascade behavior apply to versions/proposals. Normal vacancy deletion is rejected while letters exist, preventing silent loss of history; confirmed whole-account deletion cascades. Privacy export adds all three sections and validates bounded owned snapshots without operation keys. Backup inventory includes all three tables. Existing AI/public settings and external providers are unchanged.

## 5. Generation boundary

services/cover_letter_generation.py builds a general source-hash-bound evidence-selection prompt/schema and validates exact candidate IDs. Models cannot supply free-form factual prose or numeric scores through that contract. This is an OFFLINE contract, not a deployed Alice integration or semantic-quality proof. The real generation endpoint is deliberately unavailable; no environment flag enables it. Manual editing and clearly labelled local composition are usable without any provider. Scope requirements and missing live work remain explicit in AI005_SCOPE.md.

## 6. Interface and tests

Entry: /saved-vacancies/<id>/letters, with a link on saved detail; library /cover-letters; private /api/cover-letters/<id>; native create/save/compose/proposal-delete/version-delete/document-delete; version read/export and comparison. Global CSRF, strict form fields, active/verified ownership, no-store/noindex, fixed error codes and per-route limits apply. Unauthorized pages redirect to login, unauthorized API returns401, foreign objects404. New CSS uses ai005-only selectors and reduced-motion/focus styling. Existing templates and styles outside the saved-card integration are preserved.
