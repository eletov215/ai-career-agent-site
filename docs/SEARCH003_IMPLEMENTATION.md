# AI Career Agent — реализация SEARCH-003

| Поле | Значение |
|---|---|
| Документ | SEARCH003_IMPLEMENTATION |
| Пакет | SEARCH-003 — стабильная пагинация, сортировка и честные счётчики |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Основа кода | `ai-career-agent-site-main (13).zip` — GitHub `main` после SEARCH-002 |
| Candidate revision | `20260809_0007` |
| Следующий gate | GitHub Actions и Render production smoke |

## 1. Контрольный статус

SEARCH-003 реализован поверх подтверждённых SEARCH-001/002. Локальные compile, migration round-trip, repository/document checks и доступный pytest пройдены. Статус ВЫПОЛНЕНО не присваивается до полностью зелёного GitHub Actions, применения revision `20260809_0007` на Render и cross-page production smoke.

## 2. Цель и границы

Пакет устраняет архитектурную ошибку прежней выдачи: один и тот же `page` передавался каждому provider независимо, после чего provider slices смешивались, фильтровались, объединялись и сортировались только внутри текущего HTTP request. Это допускало повторы/пропуски между страницами и представляло сумму provider totals как точное число видимых карточек.

SEARCH-003 реализует:

- единый persistent search snapshot для одного набора фильтров и источников;
- per-provider cursor/page state;
- canonical filtering и SEARCH-002 dedup до присвоения ordinal;
- детерминированный global order с явными tie-breakers;
- стабильный committed prefix для уже показанных страниц;
- bounded incremental extension по запросу следующей страницы;
- отдельные `provider_reported_total`, `known_unique_total`, `total_is_exact`;
- TTL cleanup, не затрагивающий canonical vacancy cache.

Не входят: перенос `/vacancies/internal` на `/vacancies` (SEARCH-004), изменение dedup thresholds, AI matching, массовый upstream scan ради точного total.

## 3. Реализация

### 3.1 Persistent snapshot schema

Migration `20260809_0007_stable_search_snapshots.py` добавляет четыре изолированные таблицы:

```text
search_snapshots
search_snapshot_sources
search_snapshot_candidates
search_snapshot_items
```

`search_snapshots` хранит только SHA-256 fingerprint запроса, выбранные source keys, sort code, page size, counters, TTL, extension lease, `committed_count` и `late_arrival_count`. Raw keyword/region/salary не сохраняются в snapshot metadata.

`search_snapshot_sources` хранит per-provider `next_page`, fetched pages/items, provider-reported total, exhausted/error state.

`search_snapshot_candidates` содержит bounded normalized provider publications для materialization.

`search_snapshot_items` содержит deduplicated cards с постоянным `ordinal` и stable key.

Все дочерние rows удаляются каскадно при TTL cleanup. Таблицы не связаны с `vacancies`/`vacancy_source_records`, поэтому cleanup snapshot не может очистить основной cache.

### 3.2 Aggregation service

Добавлен `services/search_aggregation.py`:

```text
fetch provider pages
→ SEARCH-001 canonical filter
→ SEARCH-002 dedup
→ deterministic global sort
→ stable ordinal materialization
→ page slice
```

Fingerprint включает pipeline version, canonical filters, sorted selected sources и page size. Snapshot используется повторно только при полном совпадении fingerprint/source/sort/page-size; иначе создаётся новый snapshot и выдача безопасно возвращается на page 0.

### 3.3 Deterministic order

Sort keys не зависят от порядка завершения provider futures:

- `date`: published timestamp descending;
- `salary_desc` / `salary_asc`: salary, затем published timestamp;
- `relevance`: provider page/position rank внутри snapshot;
- общий tie-breaker: normalized title, company, source priority, source, external ID, stable source-key hash.

При равных датах и зарплатах порядок воспроизводим после restart.

### 3.4 Stable committed prefix

После выдачи страницы её ordinal range становится committed. Новые provider pages могут:

- дополнить уже committed multi-source card новой source publication без перемещения карточки;
- перестроить ещё не показанный tail;
- быть добавлены после committed prefix, если пришли поздно и по sort key должны были оказаться выше.

Так page 0 не меняет состав после перехода на page 1. Число поздних arrivals фиксируется в `late_arrival_count` и не увеличивается повторно при простом чтении snapshot.

### 3.5 Progressive provider coverage и latency budget

SEARCH-003 сохраняет стабильность страниц через immutable committed prefix, а не через синхронное чтение нескольких страниц каждого provider до глубины всей UI-страницы. Логическая страница интерфейса отделена от provider page и по умолчанию содержит 20 карточек (`SEARCH_PAGE_SIZE=20`).

Каждый HTTP request по умолчанию выполняет не более одного concurrent provider-page round (`SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=1`). Это ограничивает пользовательскую задержку временем самого медленного участвующего provider request плюс bounded PostgreSQL persistence. При переходе на следующую страницу snapshot дозагружается только если уже materialized tail недостаточен или выбранному source нужно продвинуть cursor.

После выдачи карточки входят в committed prefix и больше не перемещаются. Поздний результат, который по sort key должен был бы попасть выше уже показанной границы, остаётся в ещё не показанном tail и увеличивает `late_arrival_count`. Поэтому page 0/page 1 остаются воспроизводимыми без многократного синхронного prefetch.

Persistence candidate pages выполняется batch-операциями: один lookup существующих identity keys на provider page и bulk insert новых rows; materialized items также записываются bulk insert. Финальный commit boundary обновляет только metadata snapshot и не переписывает тот же item set повторно.

### 3.6 Bounded extension и concurrency

Default policy:

```text
SEARCH_PAGE_SIZE=20
SEARCH_SNAPSHOT_TTL_SECONDS=1800
SEARCH_SNAPSHOT_MAX_CANDIDATES=1200
SEARCH_SNAPSHOT_MAX_PAGES_PER_SOURCE=8
SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=1
SEARCH_SNAPSHOT_BUFFER_ITEMS=1
SEARCH_SNAPSHOT_EXTENSION_LEASE_SECONDS=90
```

Snapshot расширяется только до требуемой страницы плюс небольшой buffer. Extension lease предотвращает параллельные дублирующие provider fetches для одного snapshot. Provider failure сохраняет уже materialized pages и cursor остальных sources.

### 3.7 Honest totals

UI и result contract различают:

```text
provider_reported_total  приблизительная сумма totals площадок
known_unique_total       число уже materialized unique cards после filter/dedup
total_is_exact           true только когда все source cursors exhausted и snapshot не bounded
```

Approximate provider total больше не называется точным числом уникальных вакансий.

### 3.8 Verification endpoint

Добавлен secret-free endpoint:

```text
GET /health/search-pagination?snapshot=<opaque-uuid>
```

Он не вызывает providers и не показывает keyword, region, salary, credentials или candidate payload. Возвращаются snapshot counters, TTL, source cursor state и exact/bounded semantics.

## 4. Влияние на код и сайт

Ключевые области:

```text
app.py
config.py
database.py
domain/entities.py
models/search_snapshot.py
repositories/search_snapshots.py
services/search_aggregation.py
services/storage.py
migrations/versions/20260809_0007_stable_search_snapshots.py
templates/vacancies_unified.html
static/styles.css
operations/backup.py
compose.yaml
render.yaml
infra/vps/.env.example
tests/test_search_pagination.py
tests/test_routes.py
tests/test_config.py
tests/test_database.py
tests/test_postgresql_integration.py
.github/workflows/ci.yml
docs/
```

Пользовательское влияние:

- `Назад/Далее` работают внутри одного snapshot ID;
- соседние страницы не должны повторять карточки;
- summary честно отличает exact и preliminary count;
- provider totals маркируются как приблизительные;
- истёкший или несовместимый snapshot автоматически начинает поиск с page 0;
- визуальная концепция карточек/фильтров не меняется.

## 5. Проверки и доказательства

Локально подтверждены:

```text
Python compileall: passed
full available pytest: 182 passed, 6 skipped
SEARCH-003 focused suite: 18 passed
SQLite migration 0006 -> 0007 -> 0006 -> 0007: passed
Alembic check: passed
repository hygiene: passed
INFRA manifest validation: passed
document structure validation: passed
```

Focused tests проверяют stable boundaries, restart persistence, cross-page duplicate, deterministic ties, per-provider coverage/global boundary, provider failure, exact total semantics, mismatched snapshot restart, late-arrival policy, TTL cleanup isolation и migration round-trip.

Локальные skips относятся к Flask/Psycopg/real PostgreSQL service. GitHub Actions обязан выполнить их без skip, включая новый step `Verify SEARCH-003 stable pagination and totals controls`.

## 6. Ограничения и риски

- Exact total появляется только после исчерпания всех bounded source cursors; он не обещается для 90k+ upstream results в одном request.
- Snapshot materializes public vacancy data, но не сохраняет пользовательский query text в metadata.
- Provider datasets могут измениться после snapshot creation; committed pages остаются стабильными, а late arrivals добавляются после committed prefix.
- Snapshot storage ограничен TTL/candidate/page caps; при достижении cap `bounded=true`, `total_is_exact=false`.
- Relevance разных providers не сопоставима численно; используется deterministic provider page rank.
- Snapshot cleanup сейчас выполняется opportunistically и bounded при search request; отдельный scheduler можно добавить позже без изменения schema.

## 7. Rollback

1. Откатить application commit и выполнить redeploy.
2. Не очищать `vacancies` и `vacancy_source_records`.
3. Additive revision `0007` может остаться при application rollback, если старый код не обращается к snapshot tables.
4. Controlled downgrade до `0006` выполнять только после verified backup и после развертывания совместимого старого кода.
5. Downgrade удаляет только четыре ephemeral snapshot tables.

## 8. Следующее действие

1. Загрузить candidate в branch `search-003-stable-pagination`.
2. Получить полностью зелёный GitHub Actions.
3. Merge в `main` и дождаться Render deploy.
4. Проверить `/health/ready`: `current_revision=expected_revision=20260809_0007`.
5. Выполнить одинаковый multi-source query, открыть page 0/page 1/page 0 и подтвердить отсутствие overlap/перестановки.
6. Открыть `/health/search-pagination?snapshot=<id>` и проверить counters/exact semantics.
7. После доказательств перевести SEARCH-003 в ВЫПОЛНЕНО и подготовить SEARCH-004.

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Реализованы bounded persistent snapshots, stable ordinals, deterministic global sort и honest totals candidate. |
