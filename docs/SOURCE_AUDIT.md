# AI Career Agent — аудит источников v1.4.33

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.33 |
| Дата | 24 августа 2026 |
| Проверяемый пакет | AI-BENCH-001 hotfix r1 |
| Production revision | `20260819_0014` |
| Статус | НУЖНА ПРОВЕРКА GITHUB ACTIONS |

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальный source audit — AI-BENCH-001 hotfix r1

**Документ:** AI Career Agent SOURCE_AUDIT `v1.4.33`  
**Дата:** 2026-08-24  
**Основа:** AI-BENCH-001 candidate v1.4.32, загруженный пользователем в GitHub `main`, и фактический CI failure screenshot.

### Подтверждённый дефект

| Наблюдение CI | Причина |
|---|---|
| `vacancy-match-ru-01`: unsupported value `78` at path `$` | root `dict` stringified and rescanned |
| `vacancy-match-en-01`: unsupported value `72` at path `$` | same root-container false positive |
| runner status `failed` | strict gate inherited both scoring failures |
| dedicated package job exit code `1` | `--fail-on-gate` correctly rejected the run |

### Исправленные файлы кода

- `evals/ai_bench/scoring.py`;
- `tests/test_ai_bench_scoring.py`;
- `evals/VERSION` and `evals/ai_bench/__init__.py` -> `1.0.1`;
- `scripts/check_ai_bench_package.py` version gate.

### Локальная проверка hotfix

- targeted pytest: PASS;
- AI-BENCH unit discovery: 11 tests PASS;
- deterministic package gate: PASS;
- validate + strict reference run: PASS, 8/8 cases;
- full repository suite в этом контейнере не завершилась в доступный timeout и не объявляется пройденной; authoritative next gate — GitHub Actions.

### Isolation

`app.py`, production routes, models, repositories, services, requirements и Alembic chain не менялись. Production revision остаётся `20260819_0014`.
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

## 8. Required external gate

1. Upload hotfix to GitHub `main`.
2. Confirm green `AI-BENCH-001 package gate`.
3. Confirm green full `Python tests`.
4. Preserve failure/hotfix evidence in verification status.
5. Only then continue with live models, exact IDs, current prices and manual rubric.

## 9. Status decision

`AI-BENCH-001 hotfix r1` — **НУЖНА ПРОВЕРКА GITHUB ACTIONS**.  
`AI-PROVIDER-001` — **ЗАБЛОКИРОВАН**.  
Production — unchanged at `20260819_0014`.

## 10. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.32 | 24.08.2026 | Initial AI-BENCH implementation candidate. |
| 1.4.33 | 24.08.2026 | CI failure audited; scalar-leaf numeric scorer hotfix and regression coverage prepared. |
