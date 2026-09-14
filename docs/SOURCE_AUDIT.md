# AI Career Agent - source audit v1.4.49

| Поле | Значение |
|---|---|
| Document | SOURCE_AUDIT |
| Version | 1.4.49 |
| Date | 2026-09-14 |
| Package | AI-PROVIDER-001 |
| Input | ai-career-agent-site-main (30).zip |
| Input ZIP SHA-256 | 98d7d63bb76bc310ee0b27f29e6f252e275cb40ece7c3cd9905551924a14b10b |
| Source file count | 407 |
| Canonical plan / passport | 1.4.49 / 2.63 |
| Package status | НУЖНА ПРОВЕРКА |
| Production revision | 20260819_0014; unchanged |

## 1. Source precedence and freshness

The owner's latest ZIP is the code basis. Its archive comment is `426d9f940b72ade680d75147c6b3cccdc1d3c88c`; this was read from the ZIP and not independently queried from GitHub. All 407 paths match the previously delivered grounded-v2.6.1 file contents exactly (zero changed/added/removed). Different ZIP hashes are explained by packaging, not a source diff.

The supplied plan1.4.48 (MD/DOCX/PDF), passport2.62 (PDF), audit1.4.48 (PDF), AI-BENCH verification1.16 (PDF) and canonical-index MD are the correct active versions at input. All seven hashes match FILE_INDEX. The index lists 16 companion files; nine were not uploaded separately at root but were recovered and hash-verified from the earlier canonical ZIP. Complete per-file results are in `docs/evidence/ai-provider-001/input_audit.json`.

Previous loose working copies of some canonical companions were not byte-identical to the release bundle; only hash-matching bundle files were used. This is not a defect in the seven files the user uploaded. No earlier main (19)/(28) archive is used as code.

## 2. Confirmed discrepancies and explicit reconciliation

| Finding | Source of correction | Action in this package |
|---|---|---|
| Repository docs still wait for Alice run #7 | Canonical1.4.48 + final artifact34830877796 + owner acceptance | Synchronize benchmark closure; no retest or invented scores |
| PLAN section5 claims active schema0013 | Header, readiness evidence and database.py expect0014 | Set active schema0014; retain0013 in historical PRIV evidence |
| DOC-001 card still names plan 1.4.22 / passport 2.36 / schema 0010 as current | Accepted canonical 1.4.48 closure and current package | Replace the active card with 1.4.49 / 2.63 / 0014; keep older scope as history |
| SEARCH-005 card says READY and duplicate says NEEDS_VERIFICATION | SEARCH005_VERIFICATION_STATUS v1.1 | Mark active SEARCH-005 complete; label historic candidate records |
| Section16 and immediate sequence still start with completed packages | Canonical current queue | Set current gate AI-PROVIDER-001; LEGAL-001 next after approval |
| Two early version labels say1.4.32 for PRIV closure/SEARCH candidate | Previously supplied21.08.2026 canonical evidence | Correct those labels to1.4.29/1.4.30; retain historic evidence and flag legacy log inconsistencies |
| Prior code ZIP names treated as current | New main (30) supplied now | Record new input hash; preserve older names as history |
| Passport active search list stops at004 | SEARCH-005 closure evidence | Include005 in current functional inventory |

No historical "pending" statement is allowed to override the active status block. Historical run details are retained instead of silently being rewritten as successful.

Repository `SEARCH005_VERIFICATION_STATUS` was also still v1.0. It is synchronized as v1.2 against the accepted August v1.1 report, without claiming fresh Neon admin E2E. The former candidate document is retained as dated evidence.

## 3. Accepted benchmark basis

Artifact `34830877796`, run `ai-bench-20260914T100639Z-222dfc87`: benchmark1.4, dataset1.3.6, grounded-v2.6.1, Alice8/8, zero errors/retries/unresolved hard counters. Two scenario repairs and fourteen marker cleanups are explicit. Named human acceptance is qualitative; no numerical scores were supplied.

A sanitized summary and the accepted human review were added to repository evidence. Raw artifact placeholders were not modified. The complete preceding source audit remains `docs/evidence/ai-provider-001/source-audit-before-v1.4.48.md` for historical traceability.

## 4. New provider-strategy work

Primary target Alice AI LLM; manual non-generative reserve; no unqualified auto-fallback. Four tasks in RU/EN, planned marketsRU/BY, enabled marketsempty. Dated official pricing/terms/access/payment sources are separated from proposed caps and unknown account-specific facts.

The offline specification rejects runtime activation, fake approval, unsafe logging, missing contractual waiting prerequisites, unqualified routing, unsafe retries and malformed/negative monetary settings. Canonical-status checks additionally reject false completion of the provider candidate and stale active DOC-001 versions. Decimal cost output is reproducible from recorded usage. These checks do not implement production enforcement.

Production AI integration remains disabled. The benchmark adapter lacks a production no-logging header; AI-001 must implement the agreed transport instead of blindly importing it. Legal review, actual account checks, opt-out confirmation and production-IP transport are later activation gates, not falsely reported as passed.

## 5. Code and deployment boundary

No production route, service, model, schema, dependency, template, static asset, Render manifest or accepted evals file changes. The manifest protects 223 runtime/benchmark files. New execution is restricted to offline scripts/tests and a CI verification step. The package checker accepts LF/CRLF equivalence for text checkout; release packing additionally checks exact original bytes.

Staging is Render web + clean Neon PostgreSQL in Oregon, with earlier readiness/site/search smoke accepted by the owner. Old Render data was not migrated. No new live readiness, registration delivery, account/OAuth persistence or production backup restore was run in this task. Existing Gmail-token and OPS-002/INFRA-001/LEGAL-001 release work remains open.

## 6. Verification

<!-- LOCAL-RESULTS:START -->
| Local check | Measured result |
|---|---|
| Full available pytest | 412 passed, 14 skipped, 81 subtests passed; 0 failed |
| Focused AI-PROVIDER unittest | 44 passed; subset of full suite |
| Focused accepted AI-BENCH unittest | 90 passed; subset of full suite |
| Provider policy/package gate | PASS |
| Accepted benchmark package gate | PASS, including deterministic reference 8/8 |
| Document structure / infra manifests | PASS / PASS |
| Runtime and evals byte boundary | 223 preserved files unchanged |

Local Python is 3.13; GitHub still checks the repository's declared environment. Fourteen skips require unavailable Flask/Psycopg/PostgreSQL components. They are not claimed as passed. Focused totals must not be added to the full-suite count. Exact evidence: `docs/evidence/ai-provider-001/local_verification.json`.
<!-- LOCAL-RESULTS:END -->

New GitHub CI and owner strategy approval remain external gates. Paid Alice calls are unnecessary because its accepted prompts, fixtures and scorer are unchanged. No external account, billing or production settings were changed.

## 7. Limitations and rollback

The official provider sources were checked on2026-09-14; actual eligibility, account quota, metadata retention, precise model revision and no-logging effective time are not verified. Proposed budgets are not payment authorization. The strategy does not itself authorize real personal-data processing on US staging infrastructure.

Rollback: revert this package; schema remains0014. Existing benchmark closure is a prior accepted decision, not invalidated by reverting the new strategy candidate.

New document rendering uses DOC-STD-001 v1.2: the existing palette/layout is preserved with an explicit Carlito fallback where Aptos is unavailable. The accepted benchmark verification edition is reused unchanged.

## 8. Next action and version log

Ordinary CI + explicit owner strategy approval -> close AI-PROVIDER-001 -> LEGAL-001. Do not skip directly to production AI calls.

| Version | Date | Change |
|---|---|---|
| 1.4.49 | 2026-09-14 | Latest-source audit; canonical drift reconciliation; provider strategy candidate, price/data rules and offline tests |
| 1.4.48 | 2026-09-14 | Accepted final Alice8/8 + qualitative named human closure; preserved as historical evidence |
