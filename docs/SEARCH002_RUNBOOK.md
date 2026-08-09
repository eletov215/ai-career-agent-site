# AI Career Agent — runbook проверки SEARCH-002

| Поле | Значение |
|---|---|
| Документ | SEARCH002_RUNBOOK |
| Пакет | SEARCH-002 |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ ДЛЯ CANDIDATE |
| Candidate revision | `20260809_0006` |

## 1. Контрольный статус

Runbook используется для branch/CI/Render проверки SEARCH-002. Merge запрещён при красном CI.

## 2. Подготовка

- branch создаётся от актуального `main`;
- `.github`, `.gitignore`, `.dockerignore` и dotfiles должны сохраниться;
- запрещены `.env`, secrets, DB/dump/backup/venv/cache/bytecode;
- Start Command Render не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

## 3. GitHub Actions

Проверить зелёные шаги:

```text
Verify SEARCH-002 cross-source deduplication controls
Verify SEARCH-001 vacancy contract and normalization controls
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify SEC-001 security controls
Verify OPS-001 observability controls
Verify SYNC-001 external worker controls
Verify SYNC-002 incremental freshness and cleanup controls
Verify PostgreSQL encrypted backup and restore
Build INFRA-001 container targets
Smoke-test INFRA-001 runtime image
Run tests
```

## 4. Readiness после deploy

Открыть:

```text
https://ai-career-agent-site.onrender.com/health/ready
```

Ожидается:

```text
status=ok
database.backend=postgresql
database.persistent=true
current_revision=20260809_0006
expected_revision=20260809_0006
migrations.ok=true
```

## 5. Positive dedup smoke

1. Открыть `/vacancies/internal`.
2. Выбрать минимум два доступных источника.
3. Найти known duplicate по совместимым employer/title/location/canonical fields.
4. Убедиться, что карточка одна.
5. Проверить stacked provider logos и корректное число площадок.
6. Раскрыть `Все площадки` и открыть каждую исходную ссылку.
7. Убедиться, что primary action ведёт на действующую публикацию.

Если реальная пара временно отсутствует, positive semantics подтверждаются отдельным GitHub contract test; production smoke ограничивается regression/UI проверкой.

## 6. Negative smoke

Проверить, что отдельно остаются:

- junior и senior;
- одинаковое название в разных onsite городах;
- разные работодатели;
- конфликтующие валюты/зарплатные диапазоны;
- две публикации одного provider с разными IDs.

## 7. Regression smoke

- remote/onsite/hybrid filters;
- employment/experience/currency/period filters;
- поиск без фильтров;
- отсутствие HTTP 500/traceback;
- карточки не выходят за layout;
- список площадок доступен с клавиатуры через `<details>`.

## 8. Persistence smoke

PostgreSQL integration в CI должен подтвердить:

- `dedup_key`/`dedup_version` columns и indexes;
- historical rows остаются `NULL` до refresh;
- exact duplicate разных providers получает одну canonical vacancy и две source rows;
- source с изменившейся ролью отделяется обратно в отдельную canonical vacancy.

## 9. Rollback

При ложном merge или регрессии:

1. откатить SEARCH-002 application commit;
2. redeploy;
3. не очищать vacancy/source cache;
4. оставить additive `0006` columns либо выполнить controlled downgrade только после backup;
5. сохранить request IDs/log evidence для анализа.

## 10. Следующее действие

После зелёного CI и Render smoke перевести SEARCH-002 в ВЫПОЛНЕНО и начать SEARCH-003.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Первичный GitHub/Render runbook SEARCH-002 с revision `0006`. |
