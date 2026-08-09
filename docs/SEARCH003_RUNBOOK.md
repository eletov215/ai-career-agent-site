# AI Career Agent — runbook SEARCH-003

| Поле | Значение |
|---|---|
| Документ | SEARCH003_RUNBOOK |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ ДЛЯ CANDIDATE |
| Revision | `20260809_0007` |

## 1. Контрольный статус

Runbook описывает deploy, проверку и rollback bounded search snapshots. Он не разрешает массовое сканирование providers ради exact total.

## 2. Перед deploy

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q app.py config.py database.py domain models repositories services operations migrations tests scripts infra
python -m pytest -q
python -m alembic check
```

Проверить отсутствие `.env`, secrets, DB files, dumps, backups, virtualenv, caches и bytecode.

## 3. GitHub Actions

Убедиться, что зелёные:

```text
Verify SEARCH-003 stable pagination and totals controls
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify SEARCH-002 cross-source deduplication controls
Verify PostgreSQL encrypted backup and restore
Build INFRA-001 container targets
Smoke-test INFRA-001 runtime image
Run tests
```

До зелёного CI Pull Request не объединять.

## 4. Deploy Render

Start Command не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После `Live` открыть `/health/ready` и проверить revision `20260809_0007`.

Новые обязательные Render variables отсутствуют: defaults безопасны. При необходимости можно явно задать:

```text
SEARCH_PAGE_SIZE=20
SEARCH_SNAPSHOT_TTL_SECONDS=1800
SEARCH_SNAPSHOT_MAX_CANDIDATES=1200
SEARCH_SNAPSHOT_MAX_PAGES_PER_SOURCE=8
SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=1
SEARCH_SNAPSHOT_BUFFER_ITEMS=1
SEARCH_SNAPSHOT_EXTENSION_LEASE_SECONDS=90
```

## 5. Cross-page smoke

1. Открыть `/vacancies/internal`.
2. Выбрать HH + SuperJob + Работа России; Reed можно оставить по необходимости.
3. Выполнить распространённый query без узких filters.
4. Открыть `Далее` и убедиться, что URL содержит `snapshot=<uuid>&page=1`.
5. Сравнить карточки page 0/page 1: overlap отсутствует.
6. Нажать `Назад`: page 0 и порядок совпадают с первым просмотром.
7. Обновить page 0/page 1: snapshot сохраняет границы.
8. В diagnostics проверить, что snapshot увеличивает `committed_count` постепенно, source cursors двигаются между страницами, а один пользовательский request не вызывает несколько последовательных provider rounds.

## 6. Диагностика

Открыть:

```text
/health/search-pagination?snapshot=<uuid>
```

Ключевые поля:

```text
known_unique_total
provider_reported_total
total_is_exact
bounded
committed_count
late_arrival_count
sources.<source>.next_page
sources.<source>.fetched_pages
sources.<source>.exhausted
sources.<source>.error_count
candidate_counts_by_source.<source>
expires_in_seconds
```

`total_is_exact=false` допустим, пока хотя бы один source не exhausted или snapshot bounded.

## 7. Incident actions

### Повторы между страницами

- сохранить snapshot ID и query URL;
- проверить `committed_count` и source cursors;
- не очищать vacancy cache;
- временно откатить application commit при подтверждённой регрессии.

### Пустая page 2 при `has_next`

- проверить source errors/bounded state;
- истёкший/mismatched snapshot должен перейти на page 0;
- не увеличивать max pages/candidates без измерения latency/DB size.

### Слишком большой snapshot storage

- уменьшить TTL/max candidates/max pages;
- вызвать bounded cleanup обычным search request либо maintenance script после его появления;
- не удалять canonical vacancy tables.

## 8. Rollback

1. Application revert и redeploy.
2. Оставить revision `0007`, если старый код не обращается к snapshot tables.
3. Для schema downgrade: verified backup → старый код → `alembic downgrade 20260809_0006`.
4. Убедиться, что `/health/ready` соответствует ожидаемой revision.
5. Vacancy cache, OAuth, sync checkpoints и dedup metadata не очищать.

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Deploy/verification/incident/rollback runbook для SEARCH-003 candidate. |
