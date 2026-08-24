# AI Career Agent — AI-BENCH-001 Verification Status

**Версия:** v1.0  
**Дата:** 2026-08-24  
**Пакет:** AI-BENCH-001  
**Статус:** КАНДИДАТ ГОТОВ; НУЖЕН ВНЕШНИЙ СРАВНИТЕЛЬНЫЙ ПРОГОН  
**Production revision:** `20260819_0014`

## 1. Назначение

AI-BENCH-001 создаёт воспроизводимый контур для сравнения AI-моделей до production-интеграции. Пакет оценивает четыре функции AI Career Agent:

1. анализ резюме;
2. объяснимое соответствие вакансии;
3. сопроводительное письмо;
4. адаптивные вопросы интервью.

Пакет не регистрирует production routes, не изменяет БД и не выбирает провайдера автоматически.

## 2. Реализованный состав

| Компонент | Реализация |
|---|---|
| Runner | `python -m evals.ai_bench` |
| Config | versioned JSON, env-name credentials |
| Dataset | `ai-career-agent-golden-v1`, 8 synthetic RU/EN cases |
| Schemas | 4 JSON output contracts |
| Providers | deterministic fixture, command wrapper, explicit OpenAI-compatible HTTPS endpoint |
| Scoring | schema, required paths, evidence grounding, forbidden claims, unsupported numbers |
| Performance | latency, token usage, estimated cost when usage is returned |
| Evidence | `run.json`, `report.md`, sanitized per-case responses |
| CI | `.github/workflows/ci.yml` job `ai-bench-001` |
| Tests | dataset, schema, scoring, redaction, runner/report coverage |

## 3. Выполненные проверки

```text
python -m compileall -q evals scripts/check_ai_bench_package.py tests/test_ai_bench_*.py
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
python -m evals.ai_bench validate --config evals/config/ci.json
python -m evals.ai_bench run --config evals/config/ci.json --output-dir <temp> --fail-on-gate
```

Результат package-specific gate:

| Проверка | Результат |
|---|---|
| Dataset and schema validation | PASS |
| Synthetic/PII guard | PASS |
| Reference outputs | PASS |
| Strict machine quality gate | PASS |
| Secret-redaction checks | PASS |
| Machine report generation | PASS |
| Human report generation | PASS |
| Production route/migration isolation | PASS |

Machine evidence:

- `docs/evidence/ai-bench-001/validation.json`;
- `docs/evidence/ai-bench-001/reference-run.json`;
- `docs/evidence/ai-bench-001/reference-report.md`.

## 4. Что reference-run доказывает

Reference-run подтверждает, что runner, fixtures, schemas, scoring, safety gates, artifacts and CI command work deterministically. Он нужен для regression-control benchmark-инфраструктуры.

## 5. Что reference-run не доказывает

Reference-run **не является** сравнением Yandex AI Studio, OpenAI, Claude, Kimi или другой внешней модели. Он не даёт достоверных live latency/cost/error-rate данных и не заменяет ручную оценку качества текста.

## 6. Незакрытый внешний gate

До статуса `ВЫПОЛНЕНО` необходимо:

- утвердить список кандидатов и exact model IDs;
- предоставить test credentials через environment, не помещая их в Git;
- зафиксировать актуальную цену каждого кандидата в private run config;
- выполнить все cases на одинаковом dataset fingerprint;
- повторить failed/timeout cases по принятой политике;
- заполнить human rubric минимум одним назначенным reviewer;
- сохранить sanitized comparative evidence;
- принять provider decision или зафиксировать отсутствие подходящего кандидата.

## 7. Решение по статусу

**AI-BENCH-001 implementation candidate принят. Полный пакет не закрывается до внешнего comparative run. `AI-PROVIDER-001` остаётся заблокирован.**
