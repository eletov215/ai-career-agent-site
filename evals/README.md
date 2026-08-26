# AI-BENCH-001

`evals/` is an isolated, provider-agnostic evaluation package for AI Career Agent. It does not import the Flask application, does not register production routes, does not read production user data, and does not require a database migration.

## What the package measures

- JSON/schema compliance;
- required-field coverage;
- evidence-based grounding and exact raw evidence-ID semantics;
- forbidden/invented claims, unsupported impact claims, and internal-evidence leakage in user-facing text;
- unsupported numeric claims, with explicit scenario-number provenance for interview hypotheticals;
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

The repository includes `evals/config/yandex-live.json` for the approved AI-BENCH-001 Yandex comparison. The billable job is integrated into the existing `CI` workflow and executes only on `workflow_dispatch` when `run_ai_bench_live=true`; it depends on successful ordinary tests and package gates. Credentials are read only from `AI_BENCH_YANDEX_API_KEY` / `AI_BENCH_YANDEX_FOLDER_ID`. Runtime artifacts stay outside Git; the integrated live job writes to `/tmp/ai-bench-yandex-live`. The visible `evals/artifacts/README.md` scaffold is intentionally used instead of required dotfiles, and no separate workflow filename is required.

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
- `responses/<provider>/<case>.json` - sanitized model outputs;
- `manual_review_template.json` - pending named human-writing rubric, separate from machine safety gates.

No provider may be selected from the deterministic reference run. A live comparative run plus manual rubric is the remaining external gate for AI-BENCH-001.

## Package version 1.3.0 - grounded-v2.1

Version 1.3.0 is the hardening release after live run #2. It keeps grounded-v2 evidence and deterministic match controls, then adds Unicode percent normalization, same-question scenario provenance, explicit RU/EN language consistency, vacancy-grounded `motivation` paragraphs, safe provider-envelope diagnostics and at most one bounded retry for transient/malformed responses. Live-run #2 patterns are versioned in `evals/regressions/live-run-2.json`. Grounded-v2.1 scores are not directly comparable to earlier contracts. It does not add a production AI provider.
