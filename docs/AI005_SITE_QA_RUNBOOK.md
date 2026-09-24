# AI-005 SITE QA — runbook

## 1. Before browser QA

1. Confirm the deployed revision is the green merged AI-005 SITE QA revision.
2. Confirm `REAL_DATA_SUPPORTED=False`.
3. Confirm `services/legal_policy.py` remains `release_state="DRAFT"`.
4. Confirm the QA account is an existing active/verified `SEARCH_ADMIN_EMAILS` administrator.
5. Do not paste Alice credentials, personal resumes or real vacancy/profile text into QA.
6. Do not perform a live provider call until the owner separately authorizes that billable operation.

## 2. Zero-cost browser smoke

Open `/ai-cover-letter-qa/review`, unlock the current session, then open the QA page. Select a matrix case and press **Show data for Alice**.

Expected before any live call:

- page is clearly marked synthetic;
- preview contains only the pinned Example Test Studio/Python fixture;
- real account profile/resume/vacancy text is absent;
- RU/EN, short/full and tone are visible;
- there is one **Create draft with Alice** button and no extra per-call checkbox.

Do not press the provider button while live provider/runtime controls are armed unless the billable call has been explicitly authorized.

## 3. Deterministic CI matrix

CI covers at least:

- RU short professional;
- RU full professional;
- RU short friendly;
- EN short professional;
- EN full professional;
- EN short friendly;
- admin/session isolation;
- CSRF and unknown-field rejection;
- real-account source exclusion;
- single dispatch on duplicate action;
- proposal edit/accept;
- version origin/history;
- TXT export.

Existing AI-005 r2 tests remain inherited evidence for timeout, upstream error, invalid envelope/content, factuality validation, stale source, unknown-result no-retry, concurrent duplicate dispatch, result-settlement rechecks and ledger accounting.

## 4. First real Alice SITE QA call

Only after PR CI and package gates are green:

1. identify exactly one synthetic matrix case;
2. verify current provider pricing/runtime settings separately;
3. obtain explicit owner authorization for one billable call;
4. execute only that one browser action;
5. inspect proposal quality and ledger result;
6. do not automatically repeat an unknown/timeout result.

A second live request is a new billable operation and needs a new deliberate action.

## 5. Manual acceptance after authorized live call

Verify generated proposal source Alice, edit, accept, reject on a separate run if authorized, saved version, history and TXT. Confirm logs/database contain no credential/raw provider response. Record what was actually run; do not convert unrun matrix rows to PASS.
