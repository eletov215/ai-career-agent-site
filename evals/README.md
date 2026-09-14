## Package version 1.6.1 - Alice Final run #6 atomic EN cover-letter hardening / grounded-v2.6.1

Alice Final run `ai-bench-20260913T154901Z-44d67112` (artifact `34766480932`) completed 8/8 provider calls with zero errors/retries and scored **7/8** under grounded-v2.6. The only failing case was `cover-letter-en-01`: Alice expanded sparse verified facts into three unsupported effects (consistency/visual-language, decision/user-need/product-direction, and implementation/delivery). The opening also claimed prior employer familiarity (`long admired...`) without source evidence.

Version 1.6.1 advances the dataset to `1.3.6` / `grounded-v2.6.1` while keeping benchmark/run schema `1.4`. It does not weaken any hard gate and does not auto-repair provider prose. The English cover-letter prompt now requires atomic first-person fact restatements, forbids inferred purpose/benefit/result tails, and forbids unsupported prior employer/team familiarity. The exact run #6 failure patterns and safe atomic rewrites are versioned in `evals/regressions/alice-final-run-6.json`. Production Flask routes, models, migrations and revision `20260819_0014` are unchanged.

Next gate: ordinary CI/package gate -> fresh Alice Final 8/8 under dataset 1.3.6 / grounded-v2.6.1 -> focused named human re-review of cases 1, 3, 5 and 6 -> AI-BENCH-001 closure decision.

## Package version 1.6.0 - named-human writing-quality hardening / grounded-v2.6

Alice Final run `ai-bench-20260828T114615Z-5b0d7a99` (artifact `33168005097`) passed the grounded-v2.5 machine gate **8/8** with zero provider errors/retries and all machine quality/grounding counters at 1.000. Named human reviewer **Шекунов Д.С.** then required writing revisions in four areas: softer RU resume coaching, a more actionable RU vacancy-gap recommendation, and RU/EN cover letters that read as first-person human applications without advertising unverified weaknesses.

Version 1.6.0 advances the dataset to `1.3.5` / `grounded-v2.6`. It keeps all prior evidence, numeric, impact, language, scenario and match hard gates, and adds a cover-letter presentation gate: unverified candidate-gap evidence must remain in structured internal `caveats`, visible paragraphs may not disclose those gaps or describe the writer as `candidate/applicant`, and the presentation artifact omits `caveats` entirely. The previous repair that could turn a gap-bearing paragraph into visible `motivation` is removed; only vacancy-only future intent may be reclassified. RU resume and RU/EN vacancy prompts are also tightened to improve tone/actionability without inventing a future match percentage. Production Flask routes, models, migrations and revision `20260819_0014` are unchanged.

Offline replay of the retained run #5 raw responses under grounded-v2.6 is **6/8**: both cover-letter cases are now correctly rejected because they expose unverified-gap evidence in visible paragraphs. This replay is regression evidence only. Because the generation prompts changed, the next gate is ordinary CI -> fresh Alice Final live 8/8 -> focused named human re-review of cases 1, 3, 5 and 6 -> AI-BENCH-001 closure decision.

## Package version 1.5.3 - Alice Final run #4 artifact-sanitization hotfix r1

Alice Final run `ai-bench-20260828T111023Z-62a5cc1a` (artifact `33165683757`) is the first fresh grounded-v2.5 Alice-only result to pass all **8/8** machine cases with zero provider errors/retries and zero hard-safety counters. Raw/machine/presentation audit then found two `interview-en-01` purpose strings containing grouped known evidence markers such as `(c1, c2)` and `(c1, c2, v2)`. The existing presentation sanitizer handled only one known ID per bracket pair, so seven grouped IDs survived even though `purpose` is user-facing.

Version 1.5.3 does not change prompts, provider calls, machine evidence semantics, thresholds, dataset `1.3.4`, contract `grounded-v2.5`, production routes, or database schema. It extends deterministic presentation cleanup only when an entire parenthesized/bracketed group consists exclusively of known source IDs separated by commas/semicolons; mixed or unknown groups remain unmodified and hard-fail metadata detection. The retained live raw responses replay 8/8 with 20 audited marker removals and zero residual evidence IDs in declared user-facing paths. After green ordinary CI, the remaining AI-BENCH-001 gate is the named human writing-quality rubric; another billable Alice call is not required for this sanitizer-only correction.

## Package version 1.5.2 - Alice Final v4 contract corrections

Version 1.5.2 advances the dataset to `1.3.4` / `grounded-v2.5`. It keeps all grounded-v2.4 hard safety gates and adds two narrow corrections from Alice Final run `ai-bench-20260828T102540Z-bcf4c2ed`: an audited `candidate_fit` -> `motivation` repair when future learning cites only an explicitly disclosed unverified-gap candidate fact plus vacancy evidence, and response-cardinality recognition for imperative counts of resources/approaches. Verified skills, unsupported impact, durations, percentages, salary, experience numbers and outcomes remain hard failures. The RU/EN prompts are tightened accordingly, and the Alice Final run #2 regression methods are restored to ordinary unittest discovery. No production application behavior changes.

# AI-BENCH-001

`evals/` is an isolated, provider-agnostic evaluation package for AI Career Agent. It does not import the Flask application, does not register production routes, does not read production user data, and does not require a database migration.

## What the package measures

- JSON/schema compliance;
- required-field coverage;
- evidence-based grounding and exact raw evidence-ID semantics;
- forbidden/invented claims, unsupported impact claims, and internal-evidence leakage in user-facing text;
- unsupported factual numeric claims, with exact scenario-number provenance for interview hypotheticals and a narrow non-factual response-cardinality exception;
- deterministic vacancy match scoring from weighted requirement classifications;
- request error rate;
- p50/p95 latency;
- token usage and estimated cost when a provider reports usage;
- a versioned human-review rubric, deliberately left pending until a reviewer records it.

## Safety boundary

The golden dataset is synthetic and bilingual. Every case must set `synthetic=true`. Dataset validation rejects email- and phone-like data. API credentials are referenced only by environment-variable names; result files and error messages pass through secret redaction.

## Deterministic CI gate

```bash
python -m evals.ai_bench validate --config evals/config/ci.json
python -m evals.ai_bench run \
  --config evals/config/ci.json \
  --output-dir evals/artifacts/ci \
  --fail-on-gate
```

The `reference` provider reads versioned expected outputs. It validates the runner, schemas, safety gates, scoring, and report generation. It is **not** a comparative result for an external AI vendor.

## Live candidates

The historical three-provider Yandex comparison remains available through `evals/config/yandex-live.json` and the manual `run_ai_bench_live=true` workflow input. It is retained for regression and investigative comparison, not as the next release gate.

The Alice AI LLM-only verification in `evals/config/yandex-alice-final.json` runs only on `workflow_dispatch` when `run_ai_bench_alice_final=true`, after ordinary tests and the deterministic AI-BENCH package gate have passed. Historical run `ai-bench-20260828T114615Z-5b0d7a99` satisfied the grounded-v2.5 8/8 machine gate, but the named human review required writing revisions. Grounded-v2.6 changes prompts/presentation rules, so a fresh Alice Final run is mandatory after green ordinary CI; only then is the focused named human re-review performed.

Credentials are read only from `AI_BENCH_YANDEX_API_KEY` / `AI_BENCH_YANDEX_FOLDER_ID`. Runtime artifacts stay outside Git. The comparison job writes to `/tmp/ai-bench-yandex-live`; the Alice final job writes to `/tmp/ai-bench-yandex-alice-final`. The visible `evals/artifacts/README.md` scaffold is intentionally used instead of required dotfiles.

Yandex authorization preflight: the service account needs the `ai.languageModels.user` role. The AI Studio key-creation page lists `yc.ai.languageModels.execute` for Model Gallery text generation, while current Completions guides also reference `yc.ai.foundationModels.execute`. The existing key uses `yc.ai.languageModels.execute`; because secret values and key metadata are not readable from the repository, the manual workflow preflight is the decisive check. If it returns a permission error, recreate the key through AI Studio's built-in **Create API key** flow.

For any additional provider, copy `evals/config/benchmark.example.json` outside version control, enable approved providers, fill exact model identifiers and current pricing, then set secrets in the environment. Two transports are available:

- `openai_compatible`: an explicit HTTPS chat-completions endpoint;
- `command`: a local wrapper that receives a JSON request on stdin and returns a JSON envelope on stdout.

Vendor-specific production routing, fallback policy, retention, quotas, and kill switches belong to `AI-PROVIDER-001`, not this package.

## Command-wrapper contract

Input on stdin:

```json
{
  "case_id": "resume-analysis-ru-01",
  "task": "resume_analysis",
  "language": "ru",
  "messages": [{"role": "system", "content": "..."}],
  "schema": {"type": "object"}
}
```

Output on stdout:

```json
{
  "content": {"schema-compliant": "model output"},
  "usage": {"input_tokens": 100, "output_tokens": 200},
  "metadata": {"model": "approved-model-id"}
}
```

## Artifacts

Each run writes:

- `run.json` - machine-readable evidence;
- `report.md` - human-readable comparison;
- `responses/<provider>/<case>.json` - sanitized raw structured provider output retained unchanged for audit;
- `machine/<provider>/<case>.json` - machine-scored copy after only deterministic, one-to-one scenario-provenance normalization;
- `presentation/<provider>/<case>.json` - presentation-safe copy after machine normalization plus audited removal of decorated known evidence markers, including groups made only of known IDs;
- `manual_review_template.json` - pending named human-writing rubric, separate from machine safety gates.

No provider may be selected from the deterministic reference run. Comparative runs #1-#4 established Alice AI LLM as the final candidate, and Alice Final run #4 satisfied the dedicated 8/8 machine gate. After artifact-sanitization hotfix r1 is green in ordinary CI, the remaining external gate is the named human writing-quality rubric.

## Package version 1.5.0 - Alice Final v2 provenance normalization

Version 1.5.0 advances the machine contract to benchmark `1.4`, dataset `1.3.2`, `grounded-v2.3`. Alice Final run #1 (`ai-bench-20260827T101353Z-bd9809d6`) completed all eight provider calls with zero transport errors/retries but scored 6/8 because the two interview cases exposed metadata/provenance behavior that is deterministically inferable from the known scenario inputs.

The runner now preserves raw provider output, creates a separate machine copy, and may append an `sN` only when an exact normalized scenario-number token maps to exactly one scenario fact. Repairs are recorded in `normalization.scenario_provenance_repairs`; ambiguous or unknown numbers remain unresolved hard failures. The numeric safety gate also distinguishes a tightly-scoped response-cardinality instruction such as `give 2 examples` from a factual numeric claim, while unsourced durations, percentages, salary/experience figures and outcomes remain blocked.

The retained 6/8 raw artifact replays 8/8 through the new deterministic layer with six audited scenario repairs, zero unresolved scenario violations and zero unsupported numbers. This is regression evidence only: the updated interview prompt (use each scenario at most once; avoid numeric answer-count wording) still requires a fresh Alice-only live run before human review.

`evals/regressions/alice-final-run-1.json` and `docs/evidence/ai-bench-001/alice-final-run-1-grounded-v2.3-replay.json` preserve the observed failure classes and replay evidence. Production routes and user data remain outside this package.

## Package version 1.4.1 - Alice final candidate

Version 1.4.1 keeps the grounded-v2.2 machine-scoring contract and changes only the final candidate generation instructions and regression coverage after comparative live run #4. Cover-letter prompts explicitly require literal source facts and prohibit unsupported causal or outcome language. Interview prompts explicitly require scenario provenance in the same question object whenever a scenario number is used. The scorer now records causal-effect language independently of other impact families so combined phrases cannot bypass the unsupported-impact gate.

The exact Alice failures from live run #4 and safe literal rewrites are versioned in `evals/regressions/live-run-4.json`. `evals/config/yandex-alice-final.json` contains only Alice AI LLM, and `scripts/check_ai_bench_alice_final_result.py` requires a complete 8/8 machine pass before the benchmark can proceed to named human review. This package does not connect any AI provider to production routes or user data.
