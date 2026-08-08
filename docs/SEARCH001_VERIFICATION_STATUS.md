# AI Career Agent — SEARCH-001: статус проверки

| Поле | Значение |
|---|---|
| Документ | SEARCH001_VERIFICATION_STATUS |
| Версия | 1.0 |
| Дата | 08 августа 2026 |
| Пакет | SEARCH-001 |
| Статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260808_0005` |
| Связанный план | PLAN_CURRENT 1.4.5 |

## 1. Контрольный статус

Локальная реализация пройдена. GitHub PostgreSQL/CI и Render production smoke ещё не подтверждены.

## 2. Цель проверки

Доказать, что новый contract не ломает текущие providers/cache/routes, migration совместима с PostgreSQL, а canonical filters одинаково работают после deploy.

## 3. Матрица доказательств

| Проверка | Статус | Доказательство / ожидаемый результат |
|---|---|---|
| Typed contract/enums | ПРОЙДЕНО ЛОКАЛЬНО | focused contract tests |
| HH/Reed/SuperJob/Trudvsem adapters | ПРОЙДЕНО ЛОКАЛЬНО | common keys/types and mapping tests |
| Salary/currency/date normalization | ПРОЙДЕНО ЛОКАЛЬНО | aliases, ranges, invalid values, UTC tests |
| Exact canonical filters | ПРОЙДЕНО ЛОКАЛЬНО | work/employment/experience filter tests |
| Store/repository persistence | ПРОЙДЕНО ЛОКАЛЬНО | SQLite round trip and legacy fallback |
| Migration 0005 upgrade/downgrade | ПРОЙДЕНО ЛОКАЛЬНО | Alembic round trip/check |
| Full available pytest | ПРОЙДЕНО ЛОКАЛЬНО | 139 passed, 6 skipped |
| PostgreSQL migration/integration | ОЖИДАЕТ | GitHub Actions |
| SEC/OPS/SYNC regressions | ОЖИДАЕТ | GitHub Actions |
| Backup/restore with new columns | ОЖИДАЕТ | GitHub Actions |
| Docker/container smoke | ОЖИДАЕТ | GitHub Actions |
| Render revision 0005 | ОЖИДАЕТ | `/health/ready` |
| Multi-source search smoke | ОЖИДАЕТ | HH/Reed/Trudvsem/conditional SJ pages and filters |

## 4. Обязательные GitHub steps

```text
Verify SEARCH-001 vacancy contract and normalization controls
Apply test database migrations
Verify migration metadata
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify SEC-001 / OPS-001 / SYNC-001 / SYNC-002
Verify PostgreSQL encrypted backup and restore
Validate Docker Compose
Build container targets
Smoke-test runtime image
Run tests
```

## 5. Render acceptance

```text
/health/ready -> 200
current_revision = 20260808_0005
expected_revision = 20260808_0005
database.ok = true
persistent = true
```

Затем проверить текущий vacancies route, keyword/region, remote/hybrid/onsite, employment, experience, currency/salary и отсутствие HTTP 500.

## 6. Negative checks

- unknown provider value остаётся unknown;
- malformed salary/date не вызывает exception;
- `remote=false` legacy row не становится onsite автоматически;
- provider failure изолирован и не ломает другие источники;
- duplicates между источниками намеренно остаются до SEARCH-002.

## 7. Ограничения и риски

GitHub не проверяет реальные provider credentials. Render smoke должен использовать существующие разрешённые integrations; при недоступном source фиксируется graceful degradation, а не ложный failure всей страницы.

## 8. Rollback

При CI/deploy regression откатить application commit; additive schema `0005` можно оставить. Downgrade только после backup.

## 9. Следующее действие

Загрузить candidate в отдельную ветку и не merge до полностью зелёного CI.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 08.08.2026 | Создан verification matrix SEARCH-001 |
