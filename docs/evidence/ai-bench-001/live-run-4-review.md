# AI-BENCH-001 live run #4 review

**Artifact:** `33050972910`  
**Run ID:** `ai-bench-20260827T074944Z-b93e74a2`  
**Contract:** benchmark `1.3`, dataset `1.3.0`, `grounded-v2.2`  
**Date reviewed:** 2026-08-27

## 1. Transport result

- 24/24 configured provider calls completed.
- Provider/API errors: 0.
- Retries: 0.
- Structured-output schema compliance: complete for the returned cases.
- Sanitized artifact contains no GitHub/Yandex credential values.

## 2. Machine summary

| Provider | Passed | Grounding | Clean text | p50 ms | Est. cost USD |
|---|---:|---:|---:|---:|---:|
| Alice AI LLM | 5/8 | 0.979 | 1.000 | 3763.20 | 0.047170 |
| Alice AI LLM Flash | 5/8 | 0.974 | 1.000 | 3048.30 | 0.007431 |
| YandexGPT Pro 5.1 | 4/8 | 0.953 | 0.875 | 2607.47 | 0.038984 |

The comparative quality gate remained failed. This is benchmark evidence, not a transport failure.

## 3. Alice AI LLM findings

Alice remained the leading candidate and passed all resume-analysis and vacancy-match cases plus English interview. Deterministic vacancy scores remained `67` (RU) and `71` (EN).

Three machine blockers remained:

1. `cover-letter-ru-01`: unsupported outcome language inferred from support/SLA/CRM/documentation facts. The response stated that SLA work ensured deadlines and used causal framing that was not present in candidate evidence.
2. `cover-letter-en-01`: unsupported impact was inferred from design systems and user interviews, including consistency/scalability and user-experience improvement outcomes absent from candidate evidence.
3. `interview-ru-01`: a `20%` scenario appeared in `follow_up_if_weak`, but the same question object omitted structured `s1` evidence. A visible `(s1)` marker was presentation noise and did not cure the missing provenance.

These are safety/grounding contract failures. Human writing scores must not override them.

## 4. Decision from run #4

The three-provider comparison phase is sufficient. Alice AI LLM remains the primary candidate; Flash remains a possible future low-risk/economy option, while YandexGPT Pro 5.1 is not the leading production candidate.

Before manual review, one final Alice-only verification is required with the same grounded-v2.2 machine gates but hardened generation instructions. The final run must contain only `yandex-alice-ai-llm`, complete all eight synthetic cases, contain zero provider errors, and pass 8/8 machine safety gates. Only then may the named human writing-quality rubric be completed.
