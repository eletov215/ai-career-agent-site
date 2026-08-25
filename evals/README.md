# AI-BENCH-001

`evals/` is an isolated, provider-agnostic evaluation package for AI Career Agent. It does not import the Flask application, does not register production routes, does not read production user data, and does not require a database migration.

## What the package measures

- JSON/schema compliance;
- required-field coverage;
- evidence-based grounding;
- forbidden or invented claims;
- unsupported numeric claims;
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

The repository includes `evals/config/yandex-live.json` for the approved AI-BENCH-001 Yandex comparison. It is executed only by the manual `AI-BENCH-001 Live Yandex` GitHub Actions workflow and reads credentials from `AI_BENCH_YANDEX_API_KEY` / `AI_BENCH_YANDEX_FOLDER_ID`. Runtime artifacts stay outside Git.

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
- `responses/<provider>/<case>.json` - sanitized model outputs.

No provider may be selected from the deterministic reference run. A live comparative run plus manual rubric is the remaining external gate for AI-BENCH-001.

## Package version 1.1.0

Version 1.1.0 keeps the 1.0.1 scalar-leaf hallucination fix and adds the isolated Yandex live-evaluation boundary: configurable auth scheme, model-from-environment, project header, per-case JSON Schema structured output, current Alice/YandexGPT candidate config, manual GitHub workflow and transport-only live gate. It does not add a production AI provider.
