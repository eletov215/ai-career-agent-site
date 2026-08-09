# AI Career Agent — аудит источников v1.4.9

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.9 |
| Дата | 09 августа 2026 |
| Проверяемый пакет | SEARCH-003 candidate |
| Рабочий источник кода | `ai-career-agent-site-main (13).zip` из GitHub `main` |
| Канонический план до обновления | PLAN_CURRENT 1.4.8 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.22 |
| Результат | SEARCH-003 реализован с additive migration `20260809_0007`; требуется GitHub/Render verification |

## 1. Контрольный статус

Актуальный ZIP `(13)` принят как источник действующего кода. Канонические PLAN_CURRENT 1.4.8 и PROJECT_PASSPORT 2.22 фиксируют SEARCH-001/002 как ВЫПОЛНЕНО и SEARCH-003 как следующий gate. DOC-STD-001 v1.1 остаётся обязательным.

## 2. Проверка источников

| Источник | Результат |
|---|---|
| GitHub ZIP `(13)` | `app.py`, WSGI `app:app`, migration `0006`, public SuperJob и SEARCH-002 hotfixes присутствуют |
| PLAN_CURRENT 1.4.8 | SEARCH-003 = ГОТОВО К СТАРТУ |
| PROJECT_PASSPORT 2.22 | Production revision `20260809_0006`, SEARCH-002 complete |
| SEARCH003_PREPARATION 1.0 | Persistent bounded snapshot architecture и honest total semantics определены |
| DOC-STD-001 1.1 | Единый generator/style/render-and-inspect обязателен |

## 3. Проверка ZIP до изменений

| Область | Результат |
|---|---|
| Database | PostgreSQL/Alembic `20260809_0006` |
| Search normalization | SEARCH-001 contract/filter layer присутствует |
| Dedup | SEARCH-002 service/persistence/UI/health telemetry присутствуют |
| Current route | Независимый provider `page`, provider totals до final filter/dedup |
| Partial skeleton | Snapshot ORM classes найдены, но отсутствовали migration/repository/service/route/tests integration |
| Dotfiles | `.github`, `.gitignore`, `.dockerignore` присутствуют |
| Prohibited artifacts | `.env`, secrets, DB/dump/backup/venv не обнаружены |

## 4. Реализованный SEARCH-003 scope

Добавлены/интегрированы:

```text
SearchAggregationService
SearchSnapshotRepository
SearchSnapshot / Source / Candidate / Item models
migration 20260809_0007
per-provider cursor state
per-provider coverage/global-boundary invariant
canonical filter + dedup before ordinal
deterministic sort and committed prefix
late-arrival tracking
honest total semantics
TTL cleanup isolation
/health/search-pagination
SEARCH-003 CI gate/tests/docs
```

SEARCH-002 thresholds, OAuth policy, `/vacancies` redesign и AI matching не изменялись.

## 5. Изменённые области

```text
app.py
config.py
database.py
domain/
models/search_snapshot.py
repositories/search_snapshots.py
services/search_aggregation.py
services/storage.py
operations/backup.py
migrations/versions/20260809_0007_stable_search_snapshots.py
templates/vacancies_unified.html
static/styles.css
compose.yaml
render.yaml
infra/vps/.env.example
scripts/infra_manifest_check.py
tests/
.github/workflows/ci.yml
docs/
```

## 6. Проверки

```text
compileall: passed
full available pytest: 182 passed, 6 skipped
SEARCH-003 focused tests: 18 passed
related SEARCH-002/003 tests: 34 passed
migration 0006 -> 0007 -> 0006 -> 0007: passed
alembic check: passed
repository hygiene: passed
INFRA manifest: passed
document structure: passed
```

Локальные skips: Flask, Psycopg/real PostgreSQL service и Docker-dependent route/runtime gates. Они остаются обязательными в GitHub Actions.

## 7. Риски и ограничения

- Exact global post-dedup total нельзя получать synchronous scan десятков тысяч provider rows.
- Snapshot bounded limits могут оставить `total_is_exact=false`.
- Provider datasets меняются во времени; committed prefix защищает уже показанные pages, late arrivals добавляются после него.
- Snapshot tables содержат public vacancy payload, но metadata не хранит raw user query.
- Cleanup ephemeral snapshot state не должен затрагивать canonical vacancy cache.

## 8. Rollback

Application revert без очистки vacancy/source cache. Additive `0007` может остаться. Downgrade до `0006` только после verified backup и deploy совместимого кода; удаляются только snapshot tables.

## 9. Следующее действие

```text
SEARCH-003 candidate
-> GitHub Actions
-> Render revision 0007
-> page 0/page 1/page 0 smoke
-> SEARCH-003 complete
-> SEARCH-004
```

## 10. Новые канонические версии

```text
PLAN_CURRENT 1.4.9
PROJECT_PASSPORT 2.23
SOURCE_AUDIT 1.4.9
SEARCH003_IMPLEMENTATION 1.0
SEARCH003_VERIFICATION_STATUS 1.0
SEARCH003_RUNBOOK 1.0
SEARCH003_PAGINATION_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.8 | 09.08.2026 | SEARCH-002 final verification и SEARCH-003 preparation. |
| 1.4.9 | 09.08.2026 | SEARCH-003 candidate source audit: persistent snapshot/ordinal/totals implementation, migration `0007`, tests/CI/docs. |


## SEARCH-003 latency regression — production evidence

После зелёного GitHub CI и Render revision `20260809_0007` первый реальный поиск зависал на длительной загрузке. Аудит candidate показал две причины: default `SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=3` заставлял один HTTP request синхронно расширять несколько provider pages, а `SearchSnapshotRepository.upsert_candidates` выполнял SELECT на каждую вакансию и повторно переписывал materialized items при commit boundary. Hotfix вводит `SEARCH_PAGE_SIZE=20`, rounds default `1`, batch persistence и metadata-only boundary commit. Schema остаётся `0007`; требуется повторный Render smoke.
