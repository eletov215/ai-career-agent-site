# AI-BENCH-001 Alice Final run #1 review

- Source artifact: `ai-bench-001-yandex-alice-final-33061758538.zip`
- Source run ID: `ai-bench-20260827T101353Z-bd9809d6`
- Source benchmark: `1.3`, dataset `1.3.1`, contract `grounded-v2.2`
- Provider: `yandex-alice-ai-llm`
- Transport: 8/8 calls completed, 0 provider errors, 0 retries
- Source machine result: 6/8 PASS

## 1. Confirmed failures

Only the two interview cases failed. Resume analysis, vacancy match and both cover letters passed the final candidate machine gates.

`interview-ru-01` had two independent issues:

- the exact scenario number `20%` appeared in one follow-up while `s1` was missing from that question object's `evidence_ids`;
- the phrase asking for `2-3` concrete examples was classified as an unsupported numeric claim even though it is only an answer-cardinality instruction, not a candidate fact, achievement, duration, salary or scenario parameter.

`interview-en-01` used the allowed scenario numbers `15%` and `90 days` in five follow-ups but omitted the matching `s1`/`s2` identifiers from those question objects. The numbers themselves were grounded and no unsupported factual number was introduced.

## 2. Grounded-v2.3 decision

The two observed failure classes are separated instead of weakening the safety gate globally.

1. **Unique scenario provenance repair.** If an exact normalized number token used inside one interview question maps to exactly one `kind=scenario` source fact, the machine layer may append that one source ID to the structured `evidence_ids`. The raw provider response remains stored separately, and each repair is recorded with question path, number and evidence ID. Unknown or ambiguous numbers are never repaired and remain hard failures.
2. **Instructional answer-cardinality exception.** A tightly scoped interview imperative such as `give 2 examples` / `приведите 2-3 примера` is treated as response formatting rather than a factual claim. Unsourced durations, percentages, salaries, experience years and other numeric assertions remain hard failures.

The model prompt is also tightened to use each scenario fact at most once and to avoid introducing numeric answer-count requirements when a non-numeric wording is sufficient.

## 3. Offline regression replay

The retained raw Alice Final run #1 responses were replayed through grounded-v2.3 without making a new provider call.

- original: 6/8 PASS;
- grounded-v2.3 replay: 8/8 PASS;
- deterministic scenario evidence repairs: 6;
- unresolved scenario provenance violations: 0;
- unsupported numbers after the narrow response-cardinality correction: 0.

Machine-readable replay evidence is stored in `alice-final-run-1-grounded-v2.3-replay.json`.

This replay is regression evidence only. It proves the new deterministic normalization/scoring behavior on the retained response bodies, but it cannot validate the updated generation prompt. A fresh Alice-only live verification under benchmark `1.4` / dataset `1.3.2` is still mandatory before named human writing review.

## 4. Safety boundary

Grounded-v2.3 does **not** auto-repair unsupported factual numbers or ambiguous provenance. It also does not modify cover-letter impact claims, vacancy classifications, unverified facts or user-facing semantic content. Production routes and user data remain outside AI-BENCH-001.
