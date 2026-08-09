# AI Career Agent — статус проверки SEARCH-003

| Поле | Значение |
|---|---|
| Документ | SEARCH003_VERIFICATION_STATUS |
| Пакет | SEARCH-003 |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260809_0007` |
| Блокирующий gate | GitHub Actions + Render cross-page smoke |

## 1. Контрольный статус

Candidate реализован и локально проверен. Пакет не считается ВЫПОЛНЕННЫМ до подтверждения PostgreSQL migration/integration, Flask routes, Docker/runtime regressions и production page-boundary smoke.

## 2. Цель проверки

Подтвердить, что:

- page 0 и page 1 одного snapshot не пересекаются;
- повторное открытие page 0 возвращает тот же ordered set;
- restart web process не удаляет snapshot;
- cross-page duplicate отображается один раз;
- поздняя более новая публикация не перемещает уже показанную страницу;
- provider failure не стирает materialized pages;
- глубокий Reed/Trudvsem pool не позволяет commit page boundary, пока HH/SuperJob не покрыли required depth либо не стали exhausted/bounded;
- exact total устанавливается только при исчерпании всех sources;
- approximate provider totals не показываются как exact unique total;
- TTL cleanup удаляет только snapshot state;
- query text и credentials отсутствуют в health response.

## 3. Локальные доказательства

| Проверка | Результат |
|---|---|
| SEARCH-003 focused tests | `18 passed` |
| Полный доступный pytest | `182 passed, 6 skipped` |
| Related SEARCH-002/003 suite | `34 passed` |
| Stable page boundaries | ПРОЙДЕНО |
| Per-provider coverage/global boundary | ПРОЙДЕНО |
| Restart persistence | ПРОЙДЕНО |
| Cross-page duplicate merge | ПРОЙДЕНО |
| Deterministic tie-breakers | ПРОЙДЕНО |
| Provider failure degradation | ПРОЙДЕНО |
| Approximate/exact total semantics | ПРОЙДЕНО |
| Late-arrival append policy | ПРОЙДЕНО |
| TTL cleanup isolation | ПРОЙДЕНО |
| Migration downgrade/upgrade | ПРОЙДЕНО |
| Alembic check | ПРОЙДЕНО |

## 4. GitHub gate

Ожидаемый step:

```text
Verify SEARCH-003 stable pagination and totals controls
```

Он должен пройти вместе с PostgreSQL integration, SEC/OPS/SYNC/SEARCH-001/002 regressions, encrypted backup/restore, Docker build/runtime smoke и full pytest.

## 5. Render smoke

Первый критерий:

```text
GET /health/ready
status = ok
current_revision = 20260809_0007
expected_revision = 20260809_0007
database.persistent = true
migrations.ok = true
```

Затем выполнить широкий HH + SuperJob + Trudvsem query и сохранить snapshot ID из pagination URL.

Проверка:

1. page 0 — записать `save_key`/titles;
2. page 1 — ни одна карточка page 0 не повторяется;
3. вернуться на page 0 с тем же `snapshot` — порядок совпадает;
4. обновить страницу — snapshot сохраняется;
5. `/health/search-pagination?snapshot=<id>` возвращает `known_unique_total`, `provider_reported_total`, `total_is_exact`, per-source cursor state;
6. endpoint не содержит keyword/region/salary/API credentials.

## 6. Ограничения и риски

- Production может не исчерпать provider cursors, поэтому `total_is_exact=false` является нормальным результатом.
- `provider_reported_total` не равен post-filter/dedup total.
- Истёкший snapshot должен вернуть новый page 0, а не пытаться продолжить старую page 2.
- Exact total нельзя проверять принудительным массовым scan upstream.

## 7. Rollback

Application revert без очистки vacancy cache. Revision `0007` additive; schema downgrade до `0006` только после verified backup. Snapshot tables являются ephemeral и могут быть удалены без потери canonical vacancies.

## 8. Следующее действие

```text
GitHub CI green
→ Render revision 0007
→ page 0 / page 1 / page 0 smoke
→ health/search-pagination evidence
→ SEARCH-003 COMPLETE
```

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Candidate verification checklist для persistent stable pagination и honest totals. |
