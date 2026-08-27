# AI Career Agent - аудит источников v1.4.41

**Дата:** 27.08.2026  
**Production revision:** `20260819_0014`

| Поле | Значение |
|---|---|
| Проверяемая кодовая основа | `ai-career-agent-site-main (25).zip` |
| ZIP comment | `f782a5238748004733575a985fffcc5687c46442` |
| Проверяемый пакет | AI-BENCH-001 Alice final candidate hardening |
| Evals | `1.4.1` |
| Benchmark contract | `1.3` |
| Dataset | `ai-career-agent-golden-v1` v`1.3.1`, `contract=grounded-v2.2` |
| External evidence | comparative live run #4 artifact `33050972910`; run ID `ai-bench-20260827T074944Z-b93e74a2` |
| Результат | candidate локально готов; нужен ordinary GitHub CI + Alice-only 8/8 machine run + named manual rubric |

## 1. Source precedence

The user supplied `ai-career-agent-site-main (25).zip` as the current GitHub `main` snapshot. It supersedes earlier code archives for this change. The separately supplied sanitized artifact `ai-bench-001-yandex-live-33050972910.zip` is used only as external benchmark evidence and as the source for synthetic regression patterns; credentials and production user data are not copied into the repository.

## 2. Comparative live run #4 audit

The grounded-v2.2 artifact completed 24/24 provider calls with zero provider errors and zero retries.

| Provider | Machine pass | Grounding | Clean text | p50 ms | Cost USD |
|---|---:|---:|---:|---:|---:|
| Alice AI LLM | 5/8 | 0.979 | 1.000 | 3763.20 | 0.047170 |
| Alice AI LLM Flash | 5/8 | 0.974 | 1.000 | 3048.30 | 0.007431 |
| YandexGPT Pro 5.1 | 4/8 | 0.953 | 0.875 | 2607.47 | 0.038984 |

Alice passed all resume-analysis and vacancy-match cases and remained the strongest general candidate. Its three blockers were two unsupported-impact cover-letter cases and one Russian interview scenario-provenance failure. These exact patterns are now preserved in `evals/regressions/live-run-4.json`.

The comparison phase is sufficient to narrow the final candidate to Alice AI LLM. This is not yet the production-provider decision.

## 3. Final Alice hardening audit

The isolated `evals/` package now:

- keeps the existing grounded-v2.2 schemas, deterministic vacancy score, language gate, scenario provenance, exact evidence IDs, presentation sanitizer, safe provider diagnostics and bounded retry;
- hardens only the candidate generation instructions and causal-impact detection needed after live run #4;
- requires cover-letter candidate-fit text to describe verified actions literally unless the cited candidate fact explicitly contains an outcome;
- treats causal terms as an independent impact family instead of suppressing them when another impact family is present;
- requires an explicit final interview audit of every scenario number across `question`, `purpose`, and `follow_up_if_weak`;
- adds a dedicated one-provider config `evals/config/yandex-alice-final.json`;
- adds manual-only CI input `run_ai_bench_alice_final` and job `AI-BENCH-001 Alice Final` after ordinary gates;
- adds a strict final result checker that requires exactly one Alice provider, zero errors, 8/8 machine pass and zero hard safety counters;
- leaves the three-provider comparison job available only for future investigations;
- adds no production AI route/service/model and no migration.

## 4. Local verification

| Check | Result |
|---|---|
| AI-BENCH package gate | PASS |
| AI-BENCH unit/package tests | PASS |
| Deterministic reference | 8/8 PASS |
| Dataset fingerprint | `e83621f50f1ed0a594bc9513901fa093c1815cf90ad1c7afa0d9bd4a4cfd2525` |
| Repository regression groups | 342 PASS, 14 environment-dependent skips, 15 subtests PASS |
| Repository hygiene | PASS after generated caches removed |
| Document structure | PASS |
| Infrastructure manifest | PASS |
| Python compileall | PASS with external pycache location |
| SQLite migrations | `0001 -> 0014` PASS; current/check `20260819_0014` |

The 14 local skips require the full GitHub CI Flask/Psycopg/PostgreSQL environment. GitHub Actions remains authoritative for them.

## 5. Production boundary

The final delivery is restricted to `evals/`, AI-BENCH tests/scripts, `.github/workflows/ci.yml`, documentation and benchmark evidence. Production routes, models, repositories, services, templates, static assets, dependencies, Render configuration, migrations and schema revision remain unchanged at `20260819_0014`.

GitHub/Yandex secret values are not present in source or generated benchmark evidence.

## 6. Current gate

1. Green ordinary GitHub CI on this candidate.
2. Manual `run_ai_bench_alice_final=true` on `main`.
3. Alice AI LLM must pass 8/8 machine cases with zero hard safety counters and zero provider errors.
4. Review sanitized Alice-only artifact.
5. Complete named human writing-quality rubric.
6. Only then close `AI-BENCH-001` and unblock `AI-PROVIDER-001`.

## 7. Status decision

`AI-BENCH-001 Alice final candidate` - **НУЖНА ПРОВЕРКА**.  
Previously completed packages remain **ВЫПОЛНЕНО**.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАНО**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.38 | 26.08.2026 | Live run #1 reviewed; grounded-v2 prepared. |
| 1.4.39 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 prepared. |
| 1.4.40 | 26.08.2026 | Live run #3 reviewed; grounded-v2.2 final comparative safety hardening prepared. |
| 1.4.41 | 27.08.2026 | Comparative live run #4 reviewed; Alice chosen as final candidate, prompts/regressions/strict Alice-only machine verification job added. |
