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

Production migration уже подтверждена: `/health/ready` показывает `current_revision=expected_revision=20260809_0006`, PostgreSQL persistent/ok и `status=ok`.

Для live dedup smoke SuperJob vacancy search переведён на app-level API access без обязательного user OAuth. OAuth SuperJob остаётся только для user-specific методов (резюме, contacts/applications). Это увеличивает шанс реальной duplicate-пары HH/SuperJob без искусственного login-gate.

Для ускорения production-проверки добавлен временный browser-readable endpoint `GET /health/search-dedup`. Он не инициирует provider I/O и показывает только aggregate telemetry последнего завершённого поиска текущего web process: input/output, duplicate counts, cross-source groups, exact/similarity groups и число кандидатов по источникам. Keyword, region, salary и credentials в endpoint не сохраняются и не выдаются. Это verification aid; global/persistent search metrics остаются вне SEARCH-002.

После merge hotfix:

```text
/health/ready -> 200
current_revision  = 20260809_0006
expected_revision = 20260809_0006
status            = ok
```

Затем проверить:

1. выполнить широкий поиск и открыть `/health/search-dedup`; `dedup.available=true` и `candidate_counts_by_source` подтверждают, какие площадки реально участвовали в fetched candidate set;
2. `dedup.stats.cross_source_duplicate_count` показывает число публикаций разных площадок, объединённых алгоритмом, а `cross_source_groups` — число multi-source карточек;
3. обычный поиск не даёт HTTP 500;
4. known cross-source duplicate отображается один раз;
5. карточка показывает минимум две площадки и обе исходные ссылки;
6. разные seniority/location/currency/salary остаются отдельными;
7. remote/onsite/hybrid и дополнительные filters продолжают работать;
8. существующий cache и карточки визуально не повреждены.

## 6. Ограничения и риски

Provider datasets могут не содержать удобную реальную пару duplicates в конкретный момент. В этом случае production smoke подтверждает отсутствие регрессии и revision `0006`, а positive/negative semantics подтверждаются CI contract tests. Stable total/pagination не входят в пакет.

## 7. Rollback

Application rollback может оставить additive columns `0006`. Schema downgrade до `0005` выполняется только после backup и после развертывания совместимого старого кода. Cache/source rows не удаляются.

## 8. Следующее действие

Загрузить SuperJob public-search hotfix, дождаться зелёного GitHub Actions и Render redeploy, затем выполнить широкий HH + SuperJob поиск и проверить dedup log/UI.

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Candidate verification status создан для migration `0006` и reversible dedup. |
| 1.0.1 | 09.08.2026 | Render `0006` подтверждён; SuperJob vacancy search отвязан от обязательного user OAuth для live dedup smoke. |
| 1.0.2 | 09.08.2026 | Добавлен aggregate `/health/search-dedup` для быстрой production-проверки числа cross-source duplicates без ручного поиска карточки. |
