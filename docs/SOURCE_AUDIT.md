# AI Career Agent — аудит источников v1.4.34

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.34 |
| Дата | 25 августа 2026 |
| Проверяемый пакет | AI-BENCH-001 live Yandex candidate |
| Production revision | `20260819_0014` |
| Статус | НУЖНА ПРОВЕРКА LIVE YANDEX WORKFLOW + MANUAL RUBRIC |

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальный source audit — AI-BENCH-001 live Yandex candidate

**Документ:** AI Career Agent SOURCE_AUDIT `v1.4.34`  
**Дата:** 2026-08-25  
**Основа:** `ai-career-agent-site-main (21).zip`, предоставленный пользователем как актуальный GitHub `main`, плюс screenshots green GitHub Actions and Yandex setup.

### Подтверждённые внешние факты

- GitHub run `#184` завершился Success: `Python tests` и `AI-BENCH-001 package gate` green;
- manual Alice AI LLM Playground smoke вернул корректный карьерный match без добавления отсутствующих навыков;
- Yandex folder `ai-career-agent-ai` создан;
- service account `ai-career-agent-bench` имеет роль `ai.languageModels.user`;
- пользователь создал API key и сохранил секрет и folder ID в GitHub Actions Secrets; значения в исходные материалы не передавались.

### Live candidate changes

- `evals 1.1.0`;
- manual-only `.github/workflows/ai-bench-live.yml`;
- exact current model families: Alice AI LLM, Alice AI LLM Flash, YandexGPT Pro 5.1;
- OpenAI-compatible endpoint `https://ai.api.cloud.yandex.net/v1/chat/completions`;
- `Api-Key` auth plus `OpenAI-Project` folder header;
- model URI injected from environment, so folder ID is not hardcoded;
- per-case `json_schema` structured output;
- 2026-08-25 synchronous USD pricing snapshot;
- sanitized artifact upload and separate transport gate;
- runtime `evals/artifacts` ignored from Git.

### Isolation

No changes to `app.py`, production routes, `config.py`, models/repositories/application services, `requirements.txt`, Render runtime or Alembic chain. Production revision remains `20260819_0014`.
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Источник истины

- Исходная база hotfix: full-project ZIP `v1.4.32`, ранее выданный и загруженный пользователем в GitHub `main`.
- GitHub screenshot является evidence фактического внешнего gate.
- Более позднего ZIP из GitHub после failed upload не предоставлялось; hotfix меняет только выявленный AI-BENCH scope и документацию.

## 2. Root cause analysis

`iter_paths(content)` возвращает пары для root, всех контейнеров и scalar leaves. До исправления `_unsupported_numbers()` выполнял `str(value)` для каждой пары. Поэтому root object содержал текстовое представление всех вложенных полей, включая generated `match_score`. Проверка `generated_numeric_paths` была корректной для `$.match_score`, но root path `$` не совпадал с exclusion.

Это объясняет точное CI evidence:

```text
unsupported_numbers: [{"path": "$", "value": "78"}]
unsupported_numbers: [{"path": "$", "value": "72"}]
```

## 3. Исправление и сохранённая защита

Исправление пропускает container values до numeric token extraction. Оно не ослабляет anti-hallucination gate:

- `$.match_score` разрешён как generated numeric field;
- число из source messages/facts разрешено;
- новое число в `$.recommendation` или другом narrative scalar остаётся unsupported и ломает strict gate;
- boolean/`null` по-прежнему исключены.

## 4. Regression coverage

Добавлены проверки:

1. generated score не пересканируется по root/container path;
2. неподтверждённое narrative number фиксируется по точному scalar path.

Existing checks для schema, grounding, evidence IDs, forbidden claims, report generation и redaction сохранены.

## 5. Выполненная локальная проверка

```text
python -m pytest tests/test_ai_bench_scoring.py tests/test_ai_bench_runner.py -q
9 passed, 8 subtests passed

python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
11 tests passed

python scripts/check_ai_bench_package.py
AI-BENCH-001 package gate passed
```

Full repository pytest запускался, но не завершился в лимит текущего container runtime. Поэтому full-suite статус не подменяется предположением.

## 6. Files and surfaces

### Functional hotfix

- `evals/ai_bench/scoring.py`;
- `tests/test_ai_bench_scoring.py`;
- `evals/VERSION`;
- `evals/ai_bench/__init__.py`;
- `scripts/check_ai_bench_package.py`;
- `evals/README.md`.

### Documentation/evidence

- `README.md`;
- `docs/PLAN_CURRENT.md`;
- `docs/PROJECT_PASSPORT.md`;
- `docs/SOURCE_AUDIT.md`;
- `docs/ROADMAP.md`;
- `docs/CHANGELOG.md`;
- `docs/CANONICAL_DOCUMENTS.md`;
- `docs/AI_BENCH_VERIFICATION_STATUS.md`;
- `docs/evidence/ai-bench-001/*`.

## 7. Production isolation

No changes to:

- `app.py` or route registration;
- `config.py` production settings;
- models/repositories/application services;
- `requirements.txt`;
- migrations;
- Docker/Render runtime;
- database revision.

## 8. Current external gate

The hotfix GitHub gate is complete. Current required gate:

1. Upload the live Yandex candidate to GitHub.
2. Confirm ordinary CI remains green.
3. Manually run `AI-BENCH-001 Live Yandex`.
4. Require zero provider transport/API errors and download the sanitized artifact.
5. Review machine quality/grounding/cost/latency evidence.
6. Complete the manual writing-quality rubric.
7. Only then open `AI-PROVIDER-001`.

## 9. Status decision

`AI-BENCH-001 live Yandex candidate` — **НУЖНА ПРОВЕРКА**.  
`AI-PROVIDER-001` — **ЗАБЛОКИРОВАН**.  
Production — unchanged at `20260819_0014`.

## 10. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.32 | 24.08.2026 | Initial AI-BENCH implementation candidate. |
| 1.4.33 | 24.08.2026 | CI failure audited; scalar-leaf numeric scorer hotfix and regression coverage prepared. |

| 1.4.34 | 25.08.2026 | GitHub hotfix CI confirmed green; manual Alice smoke and Yandex service account setup confirmed; live Yandex benchmark workflow candidate prepared. |
