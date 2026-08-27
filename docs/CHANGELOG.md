## 2026-08-27 - AI-BENCH-001 Alice Final v2 / grounded-v2.3 / evals 1.5.0

- Reviewed Alice Final run #1 artifact `33061758538`: 8/8 calls, 0 provider errors, 0 retries, source machine result 6/8.
- Localized both FAILs to interview structured metadata rather than transport/schema/provider failure: allowed scenario numbers lacked matching `sN` in the same question objects; RU additionally triggered an over-broad numeric gate on `2-3 примера`.
- Added raw/machine/presentation evidence separation. Raw provider output remains unchanged; machine scoring may apply only a deterministic one-to-one exact-number -> unique scenario `sN` provenance repair, with path/number/evidence ID recorded in run evidence.
- Ambiguous/unknown scenario mappings remain hard failures and no candidate/vacancy evidence or user-visible semantic text is invented by the normalizer.
- Added a narrow interview answer-cardinality exception for commands such as `2-3 примера` / `2 examples`; unsourced durations, percentages, salary, experience years, achievements and outcomes remain blocked.
- Tightened RU/EN interview prompts to avoid repeated scenario numbers and prefer nonnumeric response-cardinality wording.
- Added `evals/regressions/alice-final-run-1.json`, benchmark `1.4`, dataset `1.3.2`, `grounded-v2.3`, and report/CI visibility for audited scenario repairs.
- Offline replay of the retained raw Alice Final run #1 responses is 8/8 with six audited repairs, zero unresolved scenario violations and zero unsupported numbers. Replay is regression evidence, not a new provider result.
- Local verification: AI-BENCH 70 PASS; repository groups 348 PASS, 14 environment-dependent skips, 15 subtests PASS; deterministic reference 8/8; package/hygiene/infra/migration checks pass.
- Production routes, models, services, templates, dependencies, migrations, Render runtime and revision `20260819_0014` remain unchanged.
- Next gate: green ordinary CI -> fresh `run_ai_bench_alice_final=true` -> 8/8 machine pass -> artifact audit -> named human writing-quality rubric.

## 2026-08-27 - AI-BENCH-001 Alice final candidate / evals 1.4.1

- Reviewed comparative grounded-v2.2 live run #4 artifact `33050972910`: 24/24 calls, 0 provider errors, 0 retries; Alice AI LLM 5/8, Flash 5/8, YandexGPT Pro 5.1 4/8.
- Confirmed Alice AI LLM as the leading candidate for final verification; no production provider decision is made yet.
- Hardened cover-letter prompts to use literal evidence-bound action statements and to avoid inferred benefit/quality/speed/feasibility/UX outcomes when candidate evidence does not state them.
- Strengthened impact scoring so causal language remains an independent safety family even when another outcome family is present.
- Hardened interview prompts with a final per-question scenario-number/evidence audit.
- Added `evals/regressions/live-run-4.json`, a one-provider `evals/config/yandex-alice-final.json`, strict Alice final result checker, and manual-only `AI-BENCH-001 Alice Final` workflow job.
- Dataset prompt version is `1.3.1`; grounded-v2.2 scoring contract remains unchanged for direct gate comparability.
- Production routes, models, services, templates, dependencies, migrations, Render runtime and revision `20260819_0014` remain unchanged.
- Next gate: green ordinary CI -> `run_ai_bench_alice_final=true` -> Alice 8/8 machine pass -> named human writing-quality rubric.

## 2026-08-26 - AI-BENCH-001 grounded-v2.2 final safety hardening / evals 1.4.0

- Reviewed grounded-v2.1 live run #3 artifact `32978362483`: Alice AI LLM 7/8, Flash 4/8, YandexGPT Pro 5.1 5/8; all 24 provider calls completed without errors or retries.
- Manual safety review found a machine-missed Alice Russian cover-letter defect: source responsibilities were expanded into unsupported speed/efficiency/service-quality outcomes.
- Replaced the narrow unsupported-impact verb check with source-matched semantic impact families and added regression coverage for the real Alice phrases.
- Added `evals/regressions/live-run-3.json` for unsupported impact, repairable decorated evidence markers, hard serialized metadata and scenario provenance.
- Added post-score `presentation/<provider>/<case>.json`: only simple decorated known evidence markers may be stripped; machine scoring always uses the original payload.
- Kept missing evidence, unknown IDs, `evidence_ids:` labels, serialized schema/debug metadata and scenario-provenance violations as hard failures.
- Grounded-v2.2 replay of live-run #3 under live thresholds demonstrates the new gate catches the Alice impact defect while presentation-only marker noise is repairable.
- Local regression groups: 333 PASS, 14 environment-dependent skips, 12 subtests PASS; AI-BENCH unit tests 55 PASS; deterministic reference 8/8 PASS.
- Production routes, models, services, templates, dependencies, migrations, Render runtime and revision `20260819_0014` remain unchanged.
- Next gate: green ordinary CI -> final live run #4 -> artifact review -> named manual rubric.

## 2026-08-26 - AI-BENCH-001 grounded-v2.1 hardening / evals 1.3.0

- Reviewed grounded-v2 live run #2 artifact `32972783843`: Alice AI LLM 5/8, Flash 4/8, YandexGPT Pro 5.1 3/8 with one provider-envelope error; no provider decision made.
- Normalized percent-source numbers across ordinary/NBSP/narrow-NBSP spacing while preserving hard failures for unsourced numeric claims.
- Added same-question scenario provenance so interview scenario numbers require the matching `sN` evidence.
- Added explicit RU/EN user-facing language consistency hard gates.
- Added cover-letter `motivation` semantics: vacancy-grounded motivation is valid, while `candidate_fit` still requires candidate evidence.
- Hardened OpenAI-compatible provider diagnostics without raw response/refusal persistence and added at most one bounded retry for 429/5xx/transport/malformed-envelope failures.
- Added live-run #2 regressions and expanded AI-BENCH unit/package coverage; deterministic reference remains 8/8 PASS.
- Local repository regression groups: 328 PASS, 14 environment-dependent skips, 11 subtests PASS, 0 confirmed failures.
- Production routes, models, services, dependencies, migrations and revision `20260819_0014` remain unchanged.
- Next gate: green ordinary CI -> live run #3 -> artifact review -> named manual rubric.

## 2026-08-26 - AI-BENCH-001 grounded-v2 hardening / evals 1.2.0

- Confirmed stability r4 ordinary GitHub CI green on `main`; paid live job correctly skipped on push.
- Reviewed first manual Yandex artifact `32958938365`: 24/24 provider requests completed with zero API errors; machine quality status remained failed, so transport and quality are now separated explicitly.
- Recorded first-run evidence: Alice AI LLM 4/8, Flash 2/8, YandexGPT Pro 5.1 3/8 under the old grounded-v1 contract; no provider decision made.
- Added grounded-v2 typed source facts, exact raw evidence-ID contract, structured unverified facts/caveats, user-facing metadata leakage gate, claim/evidence checks and unsupported-impact hard gate.
- Removed model-authored vacancy `match_score`; the benchmark now derives weighted numeric match deterministically after exact requirement classification and evidence checks.
- Added scenario facts so legitimate hypothetical interview numbers are allowed only when explicitly supplied, while invented candidate-achievement numbers remain blocked.
- Added live-run #1 regression patterns and separate pending `manual_review_template.json`.
- Upgraded schemas/dataset/config contract to v2/1.1 and regenerated deterministic evidence; all 8 reference cases pass strict grounded-v2 gates.
- Production Flask routes, dependencies, models, Render settings and database revision `20260819_0014` remain unchanged.
- Next gate: green ordinary CI -> live run #2 -> artifact review -> named manual rubric.

## 2026-08-26 — AI-BENCH-001 stability hotfix r4 / evals 1.1.3

- Audited the exact GitHub ZIP after run `#201`.
- Confirmed GitHub rejected the workflow before any job ran because `${{ runner.temp }}` was referenced from `jobs.ai-bench-yandex-live.env`, where the `runner` context is unavailable.
- Replaced the output path with runner-local `/tmp/ai-bench-yandex-live`.
- Added a dependency-free package check for context roots in every job-level `env`, plus positive/negative regression tests.
- Re-ran all repository test modules in bounded groups: 301 passed, 14 environment-dependent skips, 8 subtests; package/hygiene/document/compile checks pass locally.
- Restored benchmark runtime ignore rules; they remain non-gating for browser-upload compatibility.
- GitHub Secrets remain external to code; production routes/dependencies/migrations are unchanged and revision remains `20260819_0014`.

## 2026-08-25 — AI-BENCH-001 stability hotfix r3 / evals 1.1.2

- Audited the exact GitHub ZIP after run `#196`.
- Confirmed `.github/workflows/ai-bench-live.yml` had been uploaded as extensionless `.github/workflows/ai-bench-live`; production files otherwise matched the v1.4.35 delivery.
- Moved the manual billable Yandex job into the existing `.github/workflows/ci.yml`.
- Added boolean `run_ai_bench_live` input with default `false`.
- Added `needs: tests, ai-bench-001`, preventing API calls until every historical CI gate passes.
- Added concurrency protection and retained `actions/upload-artifact@v7`.
- Updated package checker/tests to validate the integrated contract and tolerate a stale extensionless file for patch compatibility.
- Restored local artifact ignore rules without making them a package-gate dependency.
- No production code, dependency, migration or Render change; revision remains `20260819_0014`.

# Changelog

## 2026-08-25 — AI-BENCH-001 stability hotfix r2 / evals 1.1.1

- Audited GitHub Actions run `#192` and separated two test/package defects from production behavior.
- Replaced SYNC worker cache assertions that depended on a fixed publication date plus the default seven-day search filter with durable `source_status_counts` assertions.
- Replaced AI-BENCH required nested dotfiles with visible `evals/artifacts/README.md`, matching the existing browser-upload-safety regression test.
- Bumped eval package to `1.1.1`; deterministic package gate and AI-BENCH unit tests pass locally.
- Re-ran all 59 locally executable test modules in bounded chunks: 298 passed, 14 environment-dependent skips and 8 subtests; also passed SQLite migrations/Alembic/infra/document checks.
- No production route, dependency, migration or database revision change. Ordinary GitHub CI must be green before the live Yandex workflow is started.

## 2026-08-25 — AI-BENCH-001 Yandex live candidate / evals 1.1.0

- User confirmed green GitHub Actions for hotfix r1: full Python tests and dedicated AI-BENCH package gate passed.
- Manual Alice AI LLM Playground smoke passed on a career-match prompt without invented experience.
- User created an isolated Yandex Cloud folder/service account, assigned `ai.languageModels.user`, created an API key with `yc.ai.languageModels.execute`, and stored only its secret plus the folder ID in GitHub Actions Secrets. Current Yandex pages also reference `yc.ai.foundationModels.execute` for Completions, so the manual workflow preflight is the decisive authorization check; a permission error requires recreating the key through AI Studio's built-in key flow.
- Added manual-only `.github/workflows/ai-bench-live.yml`; it never runs on push/PR and reads credentials only from `AI_BENCH_YANDEX_API_KEY` and `AI_BENCH_YANDEX_FOLDER_ID`.
- Added `evals/config/yandex-live.json` for Alice AI LLM, Alice AI LLM Flash and YandexGPT Pro 5.1 using current Yandex OpenAI-compatible model URIs and a 2026-08-25 synchronous USD pricing snapshot.
- Extended the generic OpenAI-compatible adapter with configurable `Api-Key` auth, model-from-environment, `OpenAI-Project` header support, and per-case JSON Schema structured output.
- Added a transport-only post-run gate: provider API errors fail the live workflow, while machine quality failures remain benchmark evidence for review instead of being confused with infrastructure failure.
- Restored `evals/.gitignore` and `evals/artifacts/.gitkeep` so runtime benchmark output is not committed.
- Updated AI-BENCH Actions to checkout/setup-python v6 to remove the observed Node 20 deprecation warning from this job.
- Production Flask routes, dependencies, Render settings, migrations and revision `20260819_0014` remain unchanged. AI-BENCH-001 is still not complete until the live artifact and manual rubric are reviewed.

## 2026-08-24 — AI-BENCH-001 numeric scorer hotfix r1 / evals 1.0.1

- GitHub CI correctly rejected the first candidate: the strict unsupported-number gate reported generated `match_score` values `78` and `72` at the root path `$`, causing two scoring subtest failures and one runner failure.
- Root cause: `_unsupported_numbers()` stringified container nodes returned by `iter_paths()`, so nested numbers were rescanned at their parent/root path and bypassed `generated_numeric_paths` exclusions.
- Fixed the scorer to inspect scalar leaves only. Truly unsupported numbers in narrative content remain hard failures.
- Added positive and negative regression tests for generated numeric paths and unsupported narrative numbers.
- Bumped benchmark package `1.0.0 -> 1.0.1`; deterministic package gate and 11 AI-BENCH unit tests pass locally.
- Production Flask routes, dependencies, migrations and revision `20260819_0014` are unchanged. Repeat GitHub Actions remains required.

## 2026-08-20 — SEARCH-005 candidate CI hotfix r1
- Corrected an incomplete candidate package that had shipped SEARCH-005 docs/tests without the new implementation modules/integration edits.
- Added persistent `source_health_states`, admin authorization/page/API, observability instrumentation, migration `20260819_0014`, config/runtime env wiring, worker instrumentation and dedicated CI coverage.
- Removed stale root packaging artifacts from the corrected full project and hardened repository hygiene against reintroducing them.
- Local corrected split suite: 276 passed, 14 environment-dependent skips, 0 failed; external GitHub/Render/E2E remains required.
## 1.4.29 — PRIV-001 complete / SEARCH-005 prep — 19.08.2026

- GitHub Actions полностью green после CI hotfix r1, включая dedicated `Verify PRIV-001 privacy export deletion and retention controls`, PostgreSQL migrations/integration, AUTH/PROF regressions, encrypted backup/restore, Docker/Compose/runtime smoke и full tests.
- Render применил `20260813_0013`; `/health/ready` подтвердил persistent PostgreSQL, `migrations.ok=true`, `privacy_cleanup.enabled=true`, `worker_alive=true`, `last_status=ok`.
- Production export E2E: re-authenticated ZIP readable; `manifest.json`/`data.json` корректны; secret fields/credentials отсутствуют; аккаунт без assets корректно не получает `assets/`, аккаунт с university logo получает owned asset.
- Destructive throwaway-account E2E: wrong phrase/password безопасно отклоняются; correct delete clears owner subtree/session; old login/URLs fail; другой User не затронут.
- Render restart + `/profile`/PROF-002/`/resumes`/AUTH/OAuth/`/vacancies` regression и log review прошли без новых 500/Traceback/IntegrityError/migration/privacy-cleanup errors или sensitive payload.
- PRIV-001 переведён в ВЫПОЛНЕНО. SEARCH-005 — следующий пакет, ГОТОВО К СТАРТУ.


## 1.4.27 — PROF-003 complete / PRIV-001 candidate — 13.08.2026

- Final PROF-003 regression `/profile`/PROF-002/`/dashboard`/AUTH/OAuth/`/vacancies`, readiness `0012` and Render log privacy/error review were confirmed; PROF-003 is ВЫПОЛНЕНО.
- Added owner-facing `/privacy-center` with readable ZIP export and destructive account deletion protected by current password plus exact confirmation phrase.
- Export includes supported owner profile/resume/OAuth metadata and owned resume image assets while excluding password/auth token hashes and OAuth access/refresh credentials.
- Added explicit local cleanup of unified and legacy HH/SuperJob credentials before User cascade deletion; remote provider-side grant revoke is not claimed.
- Added technical retention service, one-shot CLI and periodic worker with defaults: stale pending accounts 30d, expired/revoked auth artifacts 30d, identifier-free privacy audit 180d, 24h cadence. These defaults are not final legal policy.
- Added `privacy_audit_events` via migration `20260813_0013`; audit rows deliberately have no User FK/email/provider identity/content.
- Added Render supervisor/Compose/VPS privacy-worker configuration, backup inventory, privacy UI/styles, focused tests and dedicated `Verify PRIV-001 privacy export deletion and retention controls` CI step.
- Local compile, focused tests, migration round-trip, Alembic, Jinja, hygiene and infra checks passed. PRIV-001 remains НУЖНА ПРОВЕРКА pending Pull Request CI, Render `0013` and destructive production E2E on a throwaway account.

## 1.4.24 — PROF-002 complete — 12.08.2026

- Initial Pull Request CI passed, including `Verify PROF-002 resume import review controls`; Render applied PostgreSQL revision `20260812_0011` and readiness reported `status=ok`, persistent PostgreSQL and current/expected `0011`.
- Production verification found an upload-routing defect: `/profile/import` inherited the generic 256 KiB POST limit. Hotfix r2 added the route to upload endpoints, kept the 8 MiB PROF-002 limit, added visible upload/progress/oversize UX and regression coverage; no migration change.
- Production E2E confirmed text-PDF upload, editable review, zero persistence before explicit confirmation, preservation of existing confirmed scalar values, user correction/removal, one `resume_import` version with aggregate provenance, and stale-review rejection without lost updates.
- Cross-account URL smoke confirmed User B receives a clean upload form and cannot recover User A's PDF/review from the copied `/profile/import` URL; token owner-binding remains covered by dedicated CI.
- Non-PDF and image-only PDF failures were safe and did not change profile history. A corrupt-PDF manual fixture was unavailable; parser failure paths remain automated-test coverage.
- Render restart preserved confirmed profile/import history; mobile review and final dashboard/auth/OAuth/vacancy-search/log/readiness regression were reported working normally.
- English CV quality observation: deterministic extraction can produce low-confidence or incorrect structural suggestions on nonstandard layouts; mandatory review prevented automatic corruption. OCR/AI extraction remains future scope.
- PROF-002 is ВЫПОЛНЕНО. Next package: PROF-003.

## 1.4.23 — PROF-002 candidate — 12.08.2026

- Verified uploaded `ai-career-agent-site-main (16).zip` as exact GitHub `main` commit `f5e513f0f992b20305fbef36851ef97576013c86`.
- Added authenticated text-PDF import and full editable PROF-001 review; profile/history remain unchanged before explicit confirmation.
- Added deterministic `ResumeImportService` proposals for positioning, contacts, geography, skills, employment, education, languages and achievements with confidence, warnings, conflicts and bounded evidence.
- Preserved existing confirmed scalar facts on conflict and merged lists/rows without implicit deletion.
- Added a 30-minute signed review token bound to HMAC owner fingerprint and base profile version; token excludes filename, raw text and profile facts.
- Added migration `20260812_0011` with `source_kind` and aggregate `provenance_json` on immutable profile versions; canonical profile schema remains version 1.
- Added upload/review/history UI, owner/privacy-safe logging, migration/service/route/parser/PostgreSQL tests and dedicated PROF-002 CI gate.
- Local verification: `246 passed, 10 skipped`; focused `15 passed`; compile/Jinja/SQLite round-trip/Alembic check passed.
- Status remains НУЖНА ПРОВЕРКА pending Pull Request CI, Render `0011` and production E2E.

## 1.4.21 — PROF-001 partial-profile hotfix — 12.08.2026

- Initial PROF-001 Pull Request CI passed and Render successfully migrated production PostgreSQL to `20260811_0010`.
- Production E2E found a false-required validation defect: blank repeatable form rows still submitted default select values and were treated as entered records.
- Updated repeatable-row detection to ignore only default-only `employment_current=0`, `skill_level=unspecified`, and `language_level=unspecified` rows.
- Preserved strict validation when a user actually starts entering a repeatable record.
- Added service and browser-shaped route regression tests for partial profile save.
- No database migration or environment variable changes. PROF-001 remains НУЖНА ПРОВЕРКА pending hotfix CI/redeploy and resumed production E2E.

## 1.4.20 — PROF-001 candidate — 11.08.2026

- Added owner-scoped `career_profiles` and immutable `career_profile_versions`.
- Added Alembic `20260811_0010` with unique owner/current and profile/version constraints.
- Added canonical structured sections for positioning, contacts, goals, geography, salary, skills, employment, achievements, education and languages.
- Added bounded validation, canonical JSON/content hash, completion indicator and optimistic stale-editor conflict.
- Added `/profile`, `/profile/edit`, `/profile/history` and read-only version views.
- Integrated profile completion into dashboard, navigation and responsive UI.
- Added backup inventory, migration/service/route/PostgreSQL tests and dedicated PROF-001 CI gate.
- Added PROF001 implementation, verification, runbook and profile reference docs.
- Status remains НУЖНА ПРОВЕРКА pending Pull Request CI, Render `0010` and production owner/version/restart E2E.

## 1.4.19 — AUTH-002 complete — 11.08.2026

- GitHub CI, Render `20260811_0009`, HeadHunter/SuperJob ownership E2E and regression smoke confirmed.
- AUTH-002 marked ВЫПОЛНЕНО; PROF-001 became next.

Earlier history is preserved in `docs/PLAN_CURRENT.md` and previous canonical packages.

## 2026-08-13 — PROF-003 PDF education/logo parity hotfix r4

- Production E2E confirmed PDF export, but iPhone comparison exposed two presentation defects: the university emblem kept its aspect ratio in the live preview yet was distorted by the html2canvas PDF capture, and the same university name was rendered twice because the single `education` answer populated both title and detail text.
- University emblem CSS now relies on intrinsic `width/height:auto` plus bounded `max-width/max-height`, avoiding dependence on `object-fit` during html2canvas capture while preserving the same 42 px container in preview.
- Education preview now uses the resolved university name as the heading when available and hides the detail line when the user's education text is the same normalized university name; materially different education details remain visible.
- No database migration or Render environment change. Schema remains `20260812_0012`. PROF-003 remains **НУЖНА ПРОВЕРКА** pending green CI/redeploy and resumed PDF/owner/restart regression E2E.

## 2026-08-13 — PROF-003 iOS/Safari photo upload hotfix r3

- Production E2E on iPhone Safari reached photo upload after server drafts, versions, restore and stale-tab protection had passed. Selecting a valid gallery image showed the local preview but then surfaced Safari's generic `Load failed` before the asset was persisted.
- Root cause: the builder converted a generated `data:image/...;base64,...` URL to `Blob` through `fetch(dataUrl)`. Safari can reject this local `data:` fetch even though the same data URL renders in an `<img>`.
- Replaced the `fetch(dataUrl)` conversion with an in-memory base64 decode (`atob` -> `Uint8Array` -> `Blob`) before the ordinary same-origin multipart upload. Backend MIME/signature/2 MiB processed-asset controls are unchanged.
- Added a neutral Russian network error for the real server upload and restore of the previous photo/asset state when upload fails, so a failed local preview is not mistaken for a persisted photo.
- Added static frontend regression coverage. No database migration or Render environment-variable change; schema remains `20260812_0012`.
- PROF-003 remains **НУЖНА ПРОВЕРКА** pending green CI/redeploy and resumed asset/export/owner/restart regression E2E.

## 2026-08-13 — PROF-003 production E2E direct-edit hotfix r2

- Production E2E confirmed authenticated server drafts, autosave persistence across logout/login/device, multiple independent drafts, and checkpoint version 1.
- E2E exposed a usability defect in the legacy interview-only builder: after completing the interview, changing one field required replaying the whole questionnaire.
- Added a responsive `Редактировать поля` editor inside the existing resume builder. It pre-fills all eight document fields, allows changing or clearing only the needed values, updates live preview, reuses server autosave/optimistic revision protection, and does not rewrite the interview transcript.
- Education changes continue through the existing university-logo refresh path. No database migration or Render environment variable change.
- PROF-003 remains **НУЖНА ПРОВЕРКА** until hotfix CI/redeploy and resumed version/restore/conflict/asset/export/owner/restart regression E2E.

## 2026-08-13 — PROF-003 candidate v1.4.25

- Added owner-scoped server resume drafts and multiple-resume library.
- Added optimistic revision autosave with safe `409` stale conflict.
- Added immutable checkpoint/export/restore versions, history and read-only version views.
- Added durable photo/university-logo assets and export metadata tied to exact version.
- Added migration `20260812_0012`, backup inventory, owner/resource/rollback tests and dedicated CI gate.
- Removed authoritative localStorage writes; retained one-time legacy migration only.
- Synchronized repository docs that lagged canonical PROF-002 COMPLETE.
- Status: **НУЖНА ПРОВЕРКА** until CI/Render/E2E.
