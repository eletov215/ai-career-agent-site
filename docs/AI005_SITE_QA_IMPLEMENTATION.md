# AI-005 SITE QA — implementation

## Access boundary

`/ai-cover-letter-qa/review` is available only to an active, verified account already present in `SEARCH_ADMIN_EMAILS`. Enabling review stores only the current administrator ID in the signed Flask session. Other QA endpoints remain 404 until that same session is unlocked.

No new deployment flag can select `SyntheticLetterAdmission`.

## Synthetic data boundary

`AliceLetterSiteQA` accepts only language/length/tone. It loads `services/ai/letter_synthetic_cases.json` through the existing manifest hash check. Candidate facts and vacancy fields are never accepted from browser fields.

A deterministic non-login synthetic owner is created per administrator/language/manifest. The technical user has no email, normalized email or password. Its saved vacancy and profile contain only the pinned fixture. The administrator's real profile and saved vacancies are therefore outside the source graph used by the Alice request.

## Production runtime reuse

The QA generator uses:

`SyntheticLetterAdmission -> CoverLetterGenerator -> LetterRuntime -> AIRepository -> YandexAliceProvider -> validate_writing -> CoverLetterProposal`.

It does not implement a second demo provider or alternate validator. A successful validated response becomes only a pending proposal. Human accept/edit creates the existing version types; reject removes the pending private text; TXT export is only from an accepted immutable version.

## UX

The preview shows synthetic status, language, length, tone, vacancy, candidate facts, recipient and contract. The provider action is one button: **Create draft with Alice**. There is no redundant per-call checkbox. Save/accept and reject retain explicit confirmation because they mutate proposal/version state.

## Failure and idempotency

The signed preview still binds owner, letter, revision, source hash, payload hash, admission scope, parameters and operation key. The runtime performs preflight before reservation, again before provider dispatch and at settlement. Unknown timeout/upstream results are not automatically retried. A replay cannot produce a second provider dispatch.

Provider/raw transport exceptions, secrets and raw response envelopes are not rendered to the browser.
