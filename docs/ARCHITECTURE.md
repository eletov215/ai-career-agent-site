# AI Career Agent — архитектура проекта

> Последнее обновление: 10 августа 2026 года  
> Текущий пакет: `SEARCH-004` — canonical vacancy route и safe public source states  
> Статус: **НУЖНА ПРОВЕРКА**; production revision остаётся `20260809_0007`

## 1. Архитектурная цель

```text
provider adapters
→ SEARCH-001 canonical normalization/filtering
→ SEARCH-002 conservative dedup
→ SEARCH-003 persistent snapshot/global ordering
→ SEARCH-004 canonical /vacancies + safe source-state presentation
```

Бизнес-логика остаётся hosting-independent: Flask/Gunicorn `app:app`, PostgreSQL через `DATABASE_URL`, schema только Alembic, Render — staging/rollback до предрелизного VPS блока.

## 2. Основные слои

```text
Flask route
  → application services
    → repositories
      → SQLAlchemy models/session
```

- `app.py` не выполняет SQL и получает persistence через `StorageServices`;
- `services/vacancy_normalizer.py` — единая contract boundary SEARCH-001;
- `services/vacancy_deduplication.py` — conservative complete-link grouping SEARCH-002;
- `services/search_aggregation.py` — bounded snapshot/cursor orchestration SEARCH-003;
- `services/source_status.py` — safe user-facing state contract SEARCH-004;
- `repositories/search_snapshots.py` — snapshot persistence;
- `models/search_snapshot.py` — isolated TTL snapshot tables.

## 3. Public routing

Canonical vacancy search:

```text
GET /vacancies
```

Compatibility route:

```text
GET /vacancies/internal
→ 308 /vacancies с raw query string без пересборки
```

Legacy redirect сохраняет repeated `source`, filters, `snapshot` и `page`, получает `Cache-Control: no-store, max-age=0` и `X-Robots-Tag: noindex`. Generated navbar/footer/home CTA, forms и pagination используют только `/vacancies`.

## 4. Persistence schema

Production revision: `20260809_0007`. SEARCH-004 migration не добавляет.

```text
search_snapshots 1 ── * search_snapshot_sources
search_snapshots 1 ── * search_snapshot_candidates
search_snapshots 1 ── * search_snapshot_items
```

Snapshot tables отделены от `vacancies`/`vacancy_source_records`. TTL cleanup каскадно удаляет только ephemeral search state и не может удалить canonical vacancy cache, OAuth или sync checkpoints.

## 5. SEARCH-003 invariants

1. Query metadata хранится как SHA-256 fingerprint, а не raw keyword/region/salary.
2. Canonical filtering и dedup выполняются до stable ordinal/page slicing.
3. Уже committed ordinal prefix не переставляется при поздних provider updates.
4. Per-provider cursor/error/exhausted state живёт в БД.
5. Один request расширяет snapshot не более чем одним provider-page round по умолчанию.
6. `provider_reported_total`, `known_unique_total` и `total_is_exact` имеют разные значения.
7. Extension bounded limits запрещают synchronous scan десятков тысяч upstream results.

## 6. SEARCH-004 source-state contract

Разрешённые public states:

```text
available
cached
degraded
auth_required
temporarily_unavailable
```

Контракт не содержит raw exception, response body, credential, token или имя environment variable. Trudvsem показывается как PostgreSQL-backed cache. HH/SuperJob/Reed показываются как live providers только при фактической настройке/ответе. Недоступный source исключается из текущего search request до provider invocation.

Подробная admin telemetry остаётся SEARCH-005.

## 7. Security/observability

- `/health/search-pagination?snapshot=<uuid>` показывает только aggregate state;
- raw query text, cookies, credentials и provider payloads в telemetry не попадают;
- provider failure сохраняет materialized pages и не ломает общую выдачу;
- canonical/legacy routes не раскрывают техническую конфигурацию;
- public source-state labels используют neutral copy.

## 8. Проверка и rollback

Candidate проверяется отдельным GitHub gate, full regression suite и Render smoke:

```text
/vacancies 200
/vacancies/internal?<query> 308 с тем же query/snapshot/page
Trudvsem cached/degraded
one-provider failure -> page 200
```

Application rollback не очищает vacancy cache и SEARCH-003 snapshots. Database downgrade не требуется; revision `0007` остаётся.
