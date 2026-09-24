# AI-005 SITE QA — synthetic Alice browser path

| Field | Value |
|---|---|
| Date | 2026-09-24 |
| Baseline | `b828596c893d59a544f9678d7b45ab6ed7f44230` |
| Package | AI-005 / SITE QA |
| Scope | admin-only, synthetic-only |
| Paid Alice calls during implementation | 0 |
| Real-data Alice | CLOSED |
| Legal policy | DRAFT |
| Yandex Cloud apply | NOT RUN |

## Goal

Verify the real cover-letter Alice pipeline through the AI Career Agent browser UI before any real personal data is allowed and before paid infrastructure migration. The browser path must reach the existing `YandexAliceProvider`, `LetterRuntime`, output validation, proposal review, version history and TXT export.

## Included

- allowlisted administrator + signed current-session unlock;
- fixed RU/EN synthetic fixtures from the existing manifest;
- an isolated technical synthetic owner derived server-side from administrator identity, language and manifest version;
- normal SavedVacancy/CareerProfile/CoverLetter/Proposal/Version persistence for that synthetic owner;
- preview of the exact application projection sent to Alice;
- one ordinary **Create draft with Alice** action without an extra per-call checkbox;
- the existing production provider adapter, ledger, idempotency and validation runtime;
- proposal edit/accept/reject, immutable version history and TXT export;
- focused mock-transport HTTP/runtime tests and a dedicated package guard.

## Explicitly excluded

No arbitrary candidate/vacancy payload, no real administrator profile/resume/vacancy content, no client-selectable admission, no environment bypass of `LegalLetterAdmission`, no activation of `REAL_DATA_SUPPORTED`, no DRAFT→ACTIVE legal switch, no production consent mutation, no Terraform apply, no Yandex Cloud resource creation and no automatic billable Alice call.

## Acceptance boundary

Green CI proves implementation and deterministic/mock behavior only. Manual browser QA is separate. A real Alice request is a separate billable operation and requires owner authorization after green PR/CI and synthetic-isolation review.
