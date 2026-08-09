# AI Career Agent — статус проверки SEARCH-002

| Поле | Значение |
|---|---|
| Документ | SEARCH002_VERIFICATION_STATUS |
| Пакет | SEARCH-002 |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260809_0006` |
| Блокирующий gate | GitHub Actions + Render search smoke |

## 1. Контрольный статус

Код candidate готов и локально проверен. Пакет не считается ВЫПОЛНЕННЫМ до подтверждения CI, production migration и поведения выдачи.

## 2. Цель проверки

Подтвердить, что dedup:

- объединяет known duplicate разных providers;
- сохраняет все source URLs/IDs и несколько source rows;
- не объединяет разные вакансии;
- детерминирован независимо от порядка provider futures;
- отменяет persisted grouping, если обновлённый source перестал совпадать;
- не ломает filters/cards/security/ops/sync regressions;
- применяет additive migration `0006` без guessing historical rows.

## 3. Локальные доказательства

| Проверка | Результат |
|---|---|
| SEARCH-002 dedup/migration suite | `15 passed` |
| Presenter source grouping | `5 passed` |
| Same-provider negative case | ПРОЙДЕНО |
| Seniority/location/currency/salary conflicts | ПРОЙДЕНО |
| Complete-link anti-chain | ПРОЙДЕНО |
| One canonical / multiple source rows | ПРОЙДЕНО |
| Reversible split after role change | ПРОЙДЕНО |
| Unsafe URL rejection | ПРОЙДЕНО |
| Migration round-trip / Alembic check | ПРОЙДЕНО |
| Python compile / template parse | ПРОЙДЕНО |

Локальная среда не содержит Flask/Psycopg/PostgreSQL service; соответствующие scenarios должен выполнить GitHub Actions без skip.

## 4. GitHub gate

Ожидаемый отдельный шаг:

```text
Verify SEARCH-002 cross-source deduplication controls
```

Он должен пройти вместе с PostgreSQL migration/integration, SEC-001, OPS-001, SYNC-001/002, SEARCH-001, encrypted backup/restore, Docker build и runtime smoke.

## 5. Render smoke

После merge:

```text
/health/ready -> 200
current_revision  = 20260809_0006
expected_revision = 20260809_0006
status            = ok
```

Затем проверить:

1. обычный поиск не даёт HTTP 500;
2. known cross-source duplicate отображается один раз;
3. карточка показывает минимум две площадки и обе исходные ссылки;
4. разные seniority/location/currency/salary остаются отдельными;
5. remote/onsite/hybrid и дополнительные filters продолжают работать;
6. существующий cache и карточки визуально не повреждены.

## 6. Ограничения и риски

Provider datasets могут не содержать удобную реальную пару duplicates в конкретный момент. В этом случае production smoke подтверждает отсутствие регрессии и revision `0006`, а positive/negative semantics подтверждаются CI contract tests. Stable total/pagination не входят в пакет.

## 7. Rollback

Application rollback может оставить additive columns `0006`. Schema downgrade до `0005` выполняется только после backup и после развертывания совместимого старого кода. Cache/source rows не удаляются.

## 8. Следующее действие

Загрузить candidate, выполнить GitHub Actions и только после зелёного CI переходить к Render smoke.

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Candidate verification status создан для migration `0006` и reversible dedup. |
