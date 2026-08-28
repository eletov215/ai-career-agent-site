# AI-BENCH-001 Alice Final run #4 review

Date: 2026-08-28

## Source artifact

- Artifact: `ai-bench-001-yandex-alice-final-33165683757.zip`
- Run ID: `ai-bench-20260828T111023Z-62a5cc1a`
- Provider: `yandex-alice-ai-llm`
- Benchmark: `1.4`
- Dataset: `ai-career-agent-golden-v1` `1.3.4`
- Contract: `grounded-v2.5`
- Provider calls: **8/8 completed**
- Machine result: **8/8 PASS**
- Provider errors: **0**
- Retries: **0**
- Mean quality: `0.999479`
- Mean grounding: `0.994792`
- Language consistency: `1.000`
- Match consistency: `1.000`
- p50 latency: `3734.228 ms`
- p95 latency: `8872.01 ms`
- Estimated run cost: `USD 0.052416386`

All hard safety counters are zero. The live machine gate is therefore satisfied.

## Artifact audit finding

Raw/machine/presentation audit found one deterministic presentation-sanitizer defect in `interview-en-01`.

The model emitted grouped known evidence markers inside two user-facing `purpose` strings:

- `(c1, c2)` and `(v1, v2)`;
- `(c1, c2, v2)`.

Grounded-v2.5 already treats simple decorated known markers such as `(s1)` or `[c1]` as repairable presentation noise. The sanitizer removed 13 simple markers from the same response, but its regex accepted only one identifier per pair of brackets. The two grouped forms therefore remained in the presentation copy even though `purpose` is explicitly part of `_USER_FACING_PATHS`.

This is an artifact-sanitization bug, not a new provider grounding or safety failure. Raw provider output remains immutable and auditable; machine evidence IDs, scenario provenance, match scoring, prompts, thresholds and production application behavior are unchanged.

## Artifact-sanitization hotfix r1

The presentation normalizer now removes a parenthesized or bracketed group only when the **entire** group consists exclusively of known source IDs separated by commas or semicolons. Each removed ID is still recorded separately in the normalization audit.

Examples that are repairable:

- `(c1, c2)`
- `(v1; v2)`
- `[c1, c2, v2]`

Mixed or unknown groups such as `(c1, z9)` are not silently cleaned. The unknown identifier remains visible to the technical-metadata detector and is a hard failure.

Exact run #4 patterns are versioned in `evals/regressions/alice-final-run-4.json` and covered by ordinary unit/package checks.

## Deterministic replay of retained raw responses

The eight retained raw provider JSON files were reprocessed locally with the hotfix. No provider call was made and no raw response was modified.

- machine cases: **8/8 PASS**;
- scenario-provenance repairs: **3**;
- cover-letter kind repairs: **0**;
- presentation marker cleanups: **20** (13 previously cleaned + 7 grouped IDs found by artifact audit);
- residual evidence IDs in declared user-facing paths: **0**;
- unsupported numbers: **0**;
- unsupported impact claims: **0**.

Machine-readable evidence: `docs/evidence/ai-bench-001/alice-final-run-4-presentation-replay.json`.

## Gate decision

The fresh Alice-only **8/8 live machine gate is complete**. A second billable Alice call is not required for this sanitizer-only correction because generation prompts, provider input/output, raw responses and machine safety semantics are unchanged. The retained raw live evidence is sufficient to verify the deterministic presentation correction.

`AI-BENCH-001` is **not yet complete**. Remaining gates:

1. merge/upload artifact-sanitization hotfix r1 and obtain green ordinary GitHub CI/package gate;
2. confirm the deterministic presentation replay remains clean in CI/repository evidence;
3. complete the named **human** writing-quality rubric for all eight presentation outputs;
4. record the final AI-BENCH-001 closure decision before unblocking `AI-PROVIDER-001`.

A model/assistant review can help pre-audit wording but cannot substitute for the package's explicitly required named human reviewer.
