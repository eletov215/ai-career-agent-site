# AI Career Agent - аудит источников v1.4.39

**Дата:** 26.08.2026  
**Production revision:** `20260819_0014`

| Поле | Значение |
|---|---|
| Проверяемая кодовая основа | `ai-career-agent-site-main (23).zip` |
| ZIP comment | `cd775f25a546d4ce0184d65dc0f3bc87adcc9ae1` |
| Проверяемый пакет | AI-BENCH-001 grounded-v2.1 hardening |
| Evals | `1.3.0` |
| Benchmark contract | `1.2` |
| Dataset | `ai-career-agent-golden-v1` v`1.2.0`, `contract=grounded-v2.1` |
| External evidence | live run #2 artifact `32972783843` |
| Результат | candidate локально готов; нужен ordinary GitHub CI + live run #3 + manual rubric |

## 1. Source precedence

The user supplied `ai-career-agent-site-main (23).zip` as the current GitHub `main` snapshot. All changes in this package are based on that archive. Live-run #2 evidence is read from the separately supplied sanitized artifact `ai-bench-001-yandex-live-32972783843.zip`; it is evidence only and is not copied wholesale into the repository.

## 2. Live run #2 audit

The artifact contains synthetic benchmark outputs only. It reports Alice AI LLM 5/8, Alice Flash 4/8 and YandexGPT Pro 5.1 3/8, with one YandexGPT Pro provider error on `cover-letter-en-01`. The old adapter could only label that response as an unsupported JSON chat-completions envelope, so the exact envelope shape could not be proven from the artifact.

The artifact also demonstrates the following regression targets: Unicode percent spacing, scenario-number provenance, RU output returned in English, a valid vacancy-only motivation paragraph, technical-ID leakage in user text, and incomplete match evidence.

## 3. Grounded-v2.1 implementation audit

The isolated `evals/` package now:

- normalizes percent tokens across regular, NBSP and narrow-NBSP spacing;
- derives allowed numeric facts from canonical `source_facts`, not arbitrary prompt prose;
- requires same-question `scenario` evidence when an interview question/purpose/follow-up uses a scenario number;
- explicitly hard-gates RU/EN user-facing language consistency;
- adds `motivation` to cover-letter paragraph kinds and requires vacancy evidence for it;
- retains candidate-evidence requirements for `candidate_fit`;
- records bounded safe provider diagnostics without raw response body or refusal text;
- allows at most one configured retry for 429/5xx/transport/malformed-envelope failures and preserves retry evidence;
- does not retry normal HTTP 4xx or model refusal;
- adds `evals/regressions/live-run-2.json` and focused unit tests for the observed second-run failures;
- keeps numeric vacancy match code-derived rather than model-authored.

## 4. Local verification

| Check | Result |
|---|---|
| AI-BENCH unit tests | 50 PASS |
| Deterministic reference | 8/8 PASS |
| Reference fingerprint | `7aaf4b72f605a13483ca00c9be63c94928e2115c209d7c3f1f48c11f92238c2f` |
| Repository regression groups | 328 PASS, 14 environment-dependent skips, 11 subtests PASS |
| AI-BENCH package gate | PASS |
| Repository hygiene | PASS after generated caches were removed |
| Document structure | PASS |
| Yandex live config validation with non-secret test environment | PASS, 3 providers |

Full GitHub Actions remains authoritative for skipped Flask/Psycopg/PostgreSQL/Docker-dependent checks.

## 5. Production boundary

No production Flask route, model, repository, service, template, static asset, runtime dependency, Render setting or Alembic migration is changed by this package. Production revision remains `20260819_0014`. GitHub/Yandex secret values are not stored in source files or generated evidence.

## 6. Current gate

1. Green ordinary GitHub CI on the grounded-v2.1 candidate.
2. Manual `run_ai_bench_live=true` on `main`.
3. Review live run #3 artifact, including retry/diagnostic evidence.
4. Complete named human writing-quality rubric.
5. Only then decide whether `AI-BENCH-001` can close and `AI-PROVIDER-001` can start.

## 7. Status decision

`AI-BENCH-001 grounded-v2.1 hardening` - **НУЖНА ПРОВЕРКА**.  
Previously completed packages remain **ВЫПОЛНЕНО**.  
`AI-PROVIDER-001` remains **ЗАБЛОКИРОВАНО**.

## 8. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.38 | 26.08.2026 | Live run #1 reviewed; grounded-v2 evidence/safety/match hardening prepared. |
| 1.4.39 | 26.08.2026 | Live run #2 reviewed; grounded-v2.1 adds language/scenario/motivation/diagnostic/retry hardening for live run #3. |
