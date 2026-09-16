# AI Career Agent - Source audit / AI-003 candidate

| Поле | Значение |
|---|---|
| Version | 1.5.4 / 2026-09-16 |
| Code baseline | ai-career-agent-site-main (33).zip |
| Archive comment | 20947f2e015097010cbe33772f7662bef4503f37 |
| Input SHA-256 | 3f46536638fb541310c15a5520dc5a445d4916d8af90baf14292c99866971533 |
| Package | AI-003 r1 / NEEDS_VERIFICATION |
| Accepted staging | 20260915_0016, from final AI-002 evidence |
| Candidate target | 20260916_0017 / staging PENDING |

## 1. Source precedence

The owner supplied main (33), it was CRC-checked and extracted before modifications. Its final AI-002 recommendation-action condition is present. The ZIP comment is literal source evidence, not an independently verified remote HEAD or CI result. No other repository was used as a code source.

The supplied final PLAN1.5.3, AI002_IMPLEMENTATION1.1, AI002_VERIFICATION_STATUS1.1, SOURCE_AUDIT1.5.3, ROADMAP and CANONICAL_DOCUMENTS PDFs (2026-09-15) establish accepted AI-002 state. LEGAL001_DEFERRED_DECISION1.3 establishes legal deferral and unresolved mail delivery. Their later decisions supersede old pending statements in the ZIP's Markdown. Original PROJECT_PASSPORT2.70 was listed in the registry but not separately supplied; this release updates available 2.69 Markdown using only verified changes and that registry, not an invented recovered 2.70 text.

## 2. Measured change boundary

`evidence/ai-003/baseline_files_sha256.json` records every input file digest, archive digest and comment. `change_boundary.json` lists the thirteen reviewed existing runtime paths with previous/current digests. The AI-001 and AI-002 original manifests remain byte-identical; their gate adapters now validate the explicit successor chain rather than blindly rejecting intended 0017 wiring.

Accepted `evals/`, earlier prompts/schemas, provider policy and all unmodified assets remain byte-preserved. No dependency version was changed. The two new reference fixtures are independent of accepted paid benchmark evidence. The complete diff is in `AI003_CHANGESET.md`. No input files are intentionally deleted. CI changes add only ordinary AI-003 checks; paid jobs stay manual-only.

## 3. Evidence limits

Local filesystem/test checks are not GitHub Actions, Render, Neon or a real browser account test. Flask and psycopg were unavailable locally; dependency installation failed because network access was unavailable. PostgreSQL 17/container and real HTTP acceptance remain CI/staging gates. The baseline full test attempt reached its time limit without a completed result; it is not listed as a passed baseline. Final local results are recorded separately in AI003_VERIFICATION_STATUS.

## 4. Known remaining work

Public AI is still disabled. LEGAL-001 and email verification are not resolved by this package. Existing staging data remains on 0016 until the owner deploys and confirms 0017. No new billable provider run, remote deployment, mail message or destructive production operation was performed.
