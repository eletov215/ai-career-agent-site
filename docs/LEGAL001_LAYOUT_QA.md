# LEGAL-001 layout QA follow-up / 2026-09-23

Status at change preparation: IMPLEMENTED / LOCAL_CHECKS_PASS / NEEDS_PRODUCTION_RETEST.

## Baseline and reported defect

Baseline main: `506fab6660afcecd6a41442a808469f26ef420f0`.
Baseline tree: `dd308e1b412c911b202c4f39708da27cf38fde1d`.
The local source snapshot reproduced this exact Git tree before editing.

The owner supplied an intermediate QA screenshot showing overlapping disclosure
text at a 1348 CSS-pixel viewport. This is a confirmed layout defect, not a
failure of the intended HTTP 409 stale-state rejection shown on the same page.

Root cause: the disclosure and consent-status cards inherited PRIV-001's
`minmax(0,1fr) auto` text/action grid. Their multiple direct paragraphs and
headings were incorrectly placed in separate columns; the auto column could
consume the available width and collapse the first column.

## Narrow correction

`templates/privacy/ai_consent.html` loads the new versioned same-origin
`static/legal001-consent.css` stylesheet and marks only this page with
`ai-consent-page`. All new selectors are scoped to that class. Document and
status cards use one shrinkable column at every width. Long policy hashes and
history identifiers wrap. Action buttons and the back link remain readable.
Shared styles, the Privacy Center export/delete cards, and the base template
are unchanged. No document wording, policy hash/version, form fields, routes,
CSRF/HMAC, rate limits, owner scoping, consent records, or AI admission are changed.
Schema remains `20260922_0021`; legal policy is DRAFT and real-data Alice CLOSED.
Paid provider calls: 0.

## Executed local checks

- Six new rendering/CSS-contract tests in `tests/test_legal001_layout.py` cover
  absent, accepted, withdrawn and conflict states, signed hidden fields, escaped
  errors, one-column layout rules and isolation from the Privacy Center.
- Focused run with existing canonical, package and document checks: 18 passed,
  32 subtests passed. All nine inherited package guards were exercised by the
  canonical tests; they were not disabled or modified.
- Offline Chromium rendered the full base/child templates and actual local CSS.
  The baseline reproduced the collapsed grid at 1348px. The corrected version
  passed 24 geometry cases: 1348, 1280, 1024, 768, 390 and 360px, each with four
  consent states. Six Privacy Center comparisons were unchanged after adding
  the scoped stylesheet. Desktop and mobile screenshots were visually reviewed.
- Browser documents were synthetic, set directly in the local browser without
  network navigation. Remote fonts/resources were not fetched; local fallback
  fonts were used. This is not production, real-device, or full accessibility QA.
- The supplied archive of 28 additional QA tests was integrity-checked against
  its manifest. Its original 28-pass log is external QA evidence, not a new run
  by this change. Those tests are not copied over the application test suite.

## Remaining verification

GitHub CI for this change: NOT RUN at commit preparation. Exact branch/PR/main
run IDs and results must be recorded in the PR after they finish; historical
CI304/310 results are not attributed to this change.

The owner's intermediate QA message reports expected 409 conflicts and working
manual-letter versions; repeat login and final consent withdrawal were still
pending. No final production PASS, deployment SHA, export result or PostgreSQL
QA completion is inferred from the screenshots.

After deployment, QA should verify the new stylesheet loads, reopen the page
with a fresh GET (old signed forms can expire), and repeat QA-12 at the reported
1348px plus 1280, 768, 390 and 360px. Check all visible sections, the conflict
message and keyboard focus. Complete the pending re-login/withdrawal separately;
never delete the working account or its consent history. Record actual results.
