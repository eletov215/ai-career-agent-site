# AI Career Agent - AI-BENCH-001 Verification Status

| Поле | Значение |
|---|---|
| Документ | AI_BENCH_VERIFICATION_STATUS |
| Версия | 1.9 |
| Дата | 27 августа 2026 |
| Пакет | AI-BENCH-001 Alice AI LLM final candidate hardening |
| Статус | НУЖНА ПРОВЕРКА GITHUB ACTIONS + ALICE-ONLY MACHINE RUN + NAMED MANUAL RUBRIC |
| Production revision | `20260819_0014` |

## 1. Confirmed comparative evidence

Comparative grounded-v2.2 live run #4 completed from artifact `33050972910` (`run_id=ai-bench-20260827T074944Z-b93e74a2`). All 24 configured provider calls completed without provider errors or retries.

Machine summary:

- **Alice AI LLM:** 5/8 passed; grounding 0.979; clean text 1.000; p50 3763.20 ms; estimated cost USD 0.047170.
- **Alice AI LLM Flash:** 5/8 passed; grounding 0.974; clean text 1.000; p50 3048.30 ms; estimated cost USD 0.007431.
- **YandexGPT Pro 5.1:** 4/8 passed; grounding 0.953; clean text 0.875; p50 2607.47 ms; estimated cost USD 0.038984.

The three-provider comparison phase is considered sufficient for model ranking. Alice AI LLM remains the leading candidate, but it is not yet a production provider.

## 2. Alice blockers found in live run #4

Alice passed both resume-analysis cases, both vacancy-match cases and English interview. Deterministic vacancy match remained `67` for RU and `71` for EN.

Three machine blockers remained:

1. `cover-letter-ru-01` - source responsibilities were expanded into unsupported causal/quality outcome language. SLA work was described as ensuring response/resolution deadlines even though the candidate facts only stated work under SLA.
2. `cover-letter-en-01` - design-system and interview activities were expanded into unsupported consistency/scalability, UX-improvement and feasibility outcomes absent from candidate evidence.
3. `interview-ru-01` - a `20%` scenario appeared in `follow_up_if_weak`, but the same question object's structured `evidence_ids` omitted `s1`. A visible `(s1)` marker is presentation noise and cannot replace structured provenance.

These failures are authoritative machine-safety findings and cannot be overridden by writing-quality scores.

## 3. Alice final hardening target

`evals 1.4.1`, benchmark `1.3`, dataset `1.3.1`, contract `grounded-v2.2` adds only the final candidate controls needed after run #4:

- cover-letter prompts require literal evidence-bound action descriptions and provide safe rewrite examples instead of unsupported impact/outcome language;
- causal language is independently machine-tracked even when another impact family appears in the same paragraph;
- interview prompts require a final scan of `question`, `purpose`, and `follow_up_if_weak` so every scenario number brings the matching `sN` into the same question object's `evidence_ids`;
- real Alice run-4 failures are versioned in `evals/regressions/live-run-4.json`;
- safe literal rewrites are regression-tested so stricter safety does not block ordinary fact statements;
- `evals/config/yandex-alice-final.json` contains exactly one live provider: `yandex-alice-ai-llm`;
- `.github/workflows/ci.yml` adds a separate manual `run_ai_bench_alice_final` input and `AI-BENCH-001 Alice Final` job;
- `scripts/check_ai_bench_alice_final_result.py` accepts only an 8/8, zero-error, zero-hard-safety-counter Alice run;
- the historical three-provider live job remains available but is not required for the final candidate gate.

## 4. Local candidate evidence

- AI-BENCH unit/package tests: PASS, including live-run-4 regressions and strict Alice-final result checker;
- deterministic grounded-v2.2 reference: 8/8 PASS;
- dataset fingerprint after prompt hardening: `e83621f50f1ed0a594bc9513901fa093c1815cf90ad1c7afa0d9bd4a4cfd2525`;
- repository regression groups: 342 passed, 14 environment-dependent skips, 15 subtests passed, 0 confirmed failures;
- package gate, repository hygiene, document structure and infrastructure manifest: PASS;
- SQLite migration chain `0001 -> 0014`, current/check `20260819_0014`: PASS;
- production application boundary remains unchanged.

The 14 local skips require the complete GitHub CI Flask/Psycopg/PostgreSQL environment and are not claimed as locally passed.

## 5. Regression replay of live run #4

The original Alice live-run-4 responses were replayed locally against the hardened scorer. Replay remains 5/8 because a replay cannot apply the new generation instructions retroactively. The same two cover letters fail unsupported-impact safety and Russian interview fails scenario provenance. This proves the machine gates remain strict while the new prompt changes must be validated by a fresh live call.

Replay evidence is stored in `docs/evidence/ai-bench-001/live-run-4-alice-final-replay.json`.

## 6. Remaining external gate

1. Upload this candidate through the normal PR/CI path.
2. Require green `Python tests` and `AI-BENCH-001 package gate` with all historical checks.
3. Do **not** run the full three-provider comparison again by default.
4. Run `Actions -> CI -> Run workflow -> run_ai_bench_alice_final=true` on `main`.
5. Require `AI-BENCH-001 Alice Final` to pass all 8 cases with zero provider errors and zero hard safety counters.
6. Download and review the sanitized Alice-only artifact.
7. Complete the named human writing-quality rubric for the eight Alice outputs.
8. Record the benchmark closure decision; only then unblock `AI-PROVIDER-001`.

## 7. Status decision

`AI-BENCH-001` remains **НУЖНА ПРОВЕРКА**.  
Alice AI LLM is the **PRIMARY CANDIDATE**, not yet a production provider.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАН**.  
No production AI provider is connected.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.6 | 26.08.2026 | Green CI + live run #1 reviewed; grounded-v2 prepared. |
| 1.7 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 added language/scenario/motivation/diagnostic/retry hardening. |
| 1.8 | 26.08.2026 | Live run #3 reviewed; grounded-v2.2 added source-matched impact safety and presentation-only marker repair. |
| 1.9 | 27.08.2026 | Live run #4 reviewed; Alice selected as final candidate, prompts hardened, causal-impact scoring tightened, run-4 regressions and dedicated Alice-only 8/8 machine gate added. |
