# AI Career Agent — аудит источников v1.4.7

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.7 |
| Дата | 09 августа 2026 |
| Проверяемый пакет | SEARCH-002 candidate |
| Рабочий источник кода | `ai-career-agent-site-main (12).zip` |
| Канонический план до обновления | PLAN_CURRENT 1.4.6 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.20 |
| Результат | Актуальный GitHub ZIP подтверждён; SEARCH-002 реализован с additive migration `20260809_0006` и ожидает GitHub/Render verification |

## 1. Контрольный статус

ZIP `(12)` принят как источник действующего кода. PLAN_CURRENT 1.4.6 и PROJECT_PASSPORT 2.20 подтверждают SEARCH-001 как ВЫПОЛНЕНО и SEARCH-002 как следующий gate. DOC-STD-001 v1.1 обязателен для активного canonical set.

## 2. Проверка источников

| Источник | Найден | Результат |
|---|---|---|
| GitHub ZIP `(12)` | Да | Актуальный main после SEARCH-001, production revision `20260808_0005` |
| PLAN_CURRENT 1.4.6 | Да | SEARCH-002 = ГОТОВО К СТАРТУ |
| PROJECT_PASSPORT 2.20 | Да | SEARCH-001 production verification подтверждена |
| DOC-STD-001 v1.1 | Да | Единый generator/style/visual QA обязателен |
| SOURCE_AUDIT 1.4.6 | Да | SEARCH-001 final state и artifact policy подтверждены |

## 3. Проверка ZIP до изменений

| Область | Результат |
|---|---|
| WSGI | `app.py`, `app:app` сохранены |
| Database | PostgreSQL/Alembic production revision `20260808_0005` |
| Search contract | SEARCH-001 canonical fields/normalizer/providers найдены |
| Data model | `Vacancy 1 — * VacancySourceRecord` поддерживает multi-source relation |
| Existing dedup | Только same-source identity; cross-source semantic merge отсутствовал |
| Dotfiles | `.github`, `.gitignore`, `.dockerignore` присутствуют |
| Prohibited artifacts | Реальные secrets, databases, backups, virtualenv, cache и bytecode в исходном ZIP не обнаружены |

## 4. Scope SEARCH-002

Канонические источники требуют:

- fingerprint по нормализованным полям;
- осторожную similarity;
- несколько source records на одной canonical vacancy;
- explainable positive/negative decisions;
- отсутствие cross-source overmerge;
- сохранение всех provider links;
- отсутствие global pagination/total redesign.

Реализация соответствует этой границе. Для versioned metadata и candidate lookup добавлена additive migration `20260809_0006`; исторический backfill не выполняется.

## 5. Реализованный результат

- `services/vacancy_deduplication.py` с version 1, hard gates и complete-link grouping;
- collapse одинаковой provider identity до cross-source pass;
- deterministic primary card и bounded explanation;
- multi-source provider links с HTTP/HTTPS validation;
- route integration после canonical filters;
- nullable dedup metadata в canonical/source tables и non-unique indexes;
- exact persistence grouping с несколькими source rows;
- reversible split при изменении source role/constraints;
- stacked provider logos и `<details>` со всеми площадками;
- positive/negative/persistence/migration/security tests;
- отдельный GitHub Actions gate;
- repository/canonical docs обновлены до PLAN 1.4.7 / passport 2.21.

## 6. Проверки

```text
SEARCH-002 dedup/migration suite: 15 passed
presenter suite: 5 passed
provider/search normalization/filter suites: passed
repository/store/sync migration regressions: passed
Python compile: passed
SQLite migration round-trip and Alembic check: passed
Jinja template parse: passed
```

GitHub PostgreSQL/Flask/Docker и Render production smoke ещё требуются.

## 7. Исключённые артефакты

```text
.env
real secrets/tokens/passwords
*.db / *.sqlite / *.dump / *.enc
backups/
virtualenv
.pytest_cache
__pycache__
*.pyc
.git
```

## 8. Ограничения и риски

- False negative предпочтительнее false positive.
- Embeddings и semantic AI merge не используются.
- Similarity работает внутри текущего агрегированного набора.
- Global total/pagination после dedup остаётся SEARCH-003.
- Real provider data может не содержать удобную duplicate pair в момент production smoke; positive semantics тогда подтверждаются CI fixtures.

## 9. Rollback

Application revert без удаления vacancy/source cache. Additive columns `0006` могут оставаться. Controlled downgrade до `0005` — только после verified backup и после развертывания совместимого старого кода.

## 10. Следующее действие

```text
SEARCH-002 candidate
-> green GitHub CI
-> Render revision 0006 + multi-source smoke
-> SEARCH-002 complete
-> SEARCH-003 start
```

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.6 | 08.08.2026 | SEARCH-001 final verification. |
| 1.4.7 | 09.08.2026 | SEARCH-002 source/code audit, migration `0006` и candidate implementation. |
