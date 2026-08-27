# AI Career Agent - аудит источников v1.4.40

**Дата:** 26.08.2026  
**Production revision:** `20260819_0014`

| Поле | Значение |
|---|---|
| Проверяемая кодовая основа | `ai-career-agent-site-main (24).zip` |
| ZIP comment | `4e7c2eb99fa21741774c65cdb8e8e2b150883354` |
| Проверяемый пакет | AI-BENCH-001 grounded-v2.2 final safety hardening |
| Evals | `1.4.0` |
| Benchmark contract | `1.3` |
| Dataset | `ai-career-agent-golden-v1` v`1.3.0`, `contract=grounded-v2.2` |
| External evidence | live run #3 artifact `32978362483`; run ID `ai-bench-20260826T141439Z-b4d94c09` |
| Результат | candidate локально готов; нужен ordinary GitHub CI + final live run #4 + named manual rubric |

## 1. Source precedence

The user supplied `ai-career-agent-site-main (24).zip` as the current GitHub `main` snapshot. All code changes in this package are based on that archive. Live-run #3 evidence is read from the separately supplied sanitized artifact `ai-bench-001-yandex-live-32978362483.zip`; only a concise review and synthetic regression patterns are stored in the repository.

## 2. Live run #3 audit

The artifact contains synthetic benchmark outputs only. It records Alice AI LLM 7/8, Alice Flash 4/8 and YandexGPT Pro 5.1 5/8 under grounded-v2.1. All 24 provider calls completed without provider errors and no retry was required.

Manual review found a material machine-missed safety issue in Alice `cover-letter-ru-01`. Candidate evidence stated support experience, SLA, CRM and documentation of typical solutions, but the response additionally inferred acceleration/efficiency and stable service-quality outcomes. These impact claims were not present in the cited candidate facts. The same run also confirmed that Alice `interview-ru-01` used a `20%` scenario without structured `s1` evidence while displaying `(s1)` in user text.

Replay of the same raw artifact through grounded-v2.2 with live thresholds is regression evidence only, not a new live score: Alice 5/8 because both cover letters now trigger unsupported-impact safety and Russian interview still fails grounding/scenario provenance; Flash 4/8 with unverified-fact, unsupported-impact and scenario-provenance failures plus 12 repairable decorated markers; YandexGPT Pro 4/8 with hard serialized metadata, match-consistency, caveat-coverage and unsupported-impact failures plus four repairable markers.

## 3. Grounded-v2.2 implementation audit

The isolated `evals/` package now:

- classifies cover-letter outcome language into semantic impact families and requires every claimed family to exist in cited candidate evidence;
- hard-fails unsupported speed/time, efficiency, quality/reliability, growth, reduction and conversion/retention outcome families;
- versions the real live-run #3 Alice impact phrases and marker patterns in `evals/regressions/live-run-3.json`;
- scores the original provider payload before any presentation repair;
- writes a separate `presentation/<provider>/<case>.json` copy where only simple decorated known evidence markers such as `(s1)` or `[c1]` may be stripped;
- keeps missing evidence, unknown IDs, `evidence_ids:` labels and serialized schema/debug metadata as hard failures;
- preserves same-question scenario provenance, deterministic vacancy match scoring, language consistency, safe provider diagnostics and one bounded retry;
- remains fully isolated from production AI routes/services/models and requires no migration.

## 4. Local verification

| Check | Result |
|---|---|
| AI-BENCH unit tests | 55 PASS |
| Deterministic reference | 8/8 PASS |
| Reference fingerprint | `1051e1c8de4e5e1df484ed1a66f933e592e998eb7fb0ef527bf3e4f8d5ce16d9` |
| Repository regression groups | 333 PASS, 14 environment-dependent skips, 12 subtests PASS |
| AI-BENCH package gate | PASS |
| Repository hygiene | PASS after generated caches were removed |
| Document structure | PASS |
| Infrastructure manifest | PASS |
| SQLite migrations | `0001 -> 0014` PASS; current/check `20260819_0014` |

The 14 local skips require the full GitHub CI Flask/Psycopg/PostgreSQL environment and are not claimed as locally passed. GitHub Actions remains authoritative for those environment-dependent checks.

## 5. Production boundary

Hash comparison against the supplied `main` archive returned `PRODUCTION_BOUNDARY_CHANGED = []` for production application boundaries. This package is limited to `evals/`, AI-BENCH tests/scripts, `.github/workflows/ci.yml`, repository documentation and benchmark evidence. Production revision remains `20260819_0014`; no production AI provider is connected. GitHub/Yandex secret values are not stored in source files or generated evidence.

## 6. Current gate

1. Green ordinary GitHub CI on the grounded-v2.2 candidate.
2. Manual `run_ai_bench_live=true` on `main`.
3. Review final live run #4 artifact, including impact/scenario/repair diagnostics.
4. Complete named human writing-quality rubric for the accepted candidate.
5. Only then decide whether `AI-BENCH-001` can close and `AI-PROVIDER-001` can start.

## 7. Status decision

`AI-BENCH-001 grounded-v2.2 final safety hardening` - **НУЖНА ПРОВЕРКА**.  
Previously completed packages remain **ВЫПОЛНЕНО**.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАНО**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.38 | 26.08.2026 | Live run #1 reviewed; grounded-v2 evidence/safety/match hardening prepared. |
| 1.4.39 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 adds language/scenario/motivation/diagnostic/retry hardening for live run #3. |
| 1.4.40 | 26.08.2026 | Live run #3 reviewed; grounded-v2.2 adds source-matched impact-family safety, live-run-3 regressions and presentation-only simple marker repair before final live run #4. |
