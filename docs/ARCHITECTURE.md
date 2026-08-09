# AI Career Agent — архитектура проекта

> Последнее обновление: 09 августа 2026 года  
> Текущий пакет: `SEARCH-003` — persistent stable pagination candidate  
> Статус: **НУЖНА ПРОВЕРКА**; candidate revision — `20260809_0007`

## 1. Архитектурная цель

```text
provider adapters
→ SEARCH-001 canonical normalization/filtering
→ SEARCH-002 conservative dedup
→ SEARCH-003 persistent snapshot/global ordering
→ stable page slice + honest totals
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
- `repositories/search_snapshots.py` — snapshot persistence;
- `models/search_snapshot.py` — isolated TTL snapshot tables.

## 3. Persistence schema

Production before package: `20260809_0006`. Candidate: `20260809_0007`.

```text
search_snapshots 1 ── * search_snapshot_sources
search_snapshots 1 ── * search_snapshot_candidates
search_snapshots 1 ── * search_snapshot_items
```

Snapshot tables отделены от `vacancies`/`vacancy_source_records`. TTL cleanup каскадно удаляет только ephemeral search state и не может удалить canonical vacancy cache, OAuth или sync checkpoints.

## 4. SEARCH-003 invariants

1. Query metadata хранится как SHA-256 fingerprint, а не raw keyword/region/salary.
2. Canonical filtering и dedup выполняются до stable ordinal/page slicing.
3. Уже committed ordinal prefix не переставляется при поздних provider updates.
4. Per-provider state (`next_page`, `fetched_pages`, `reported_total`, `exhausted`, `bounded`, errors) живёт в БД.
5. Каждый HTTP request расширяет snapshot не более чем одним provider-page round по умолчанию. Уже показанный committed prefix не перестраивается; поздние более приоритетные элементы добавляются только в ещё не показанный tail и учитываются в diagnostics.
6. `provider_reported_total`, `known_unique_total` и `total_is_exact` имеют разные значения; approximate total не выдаётся за exact post-dedup total.
7. Extension bounded limits запрещают synchronous scan десятков тысяч upstream results.

## 5. Deterministic sort

`date`, `salary_desc`, `salary_asc`, `relevance` используют общий явный tie-breaker: normalized title/company, source priority, source, external ID и stable source-key hash. Порядок не зависит от завершения provider futures.

## 6. Security/observability

- `/health/search-pagination?snapshot=<uuid>` показывает только aggregate state;
- raw query text, cookies, credentials и provider payloads в telemetry не попадают;
- provider failure сохраняет уже materialized pages и error/cursor state;
- public verification endpoint не инициирует provider I/O.

## 7. Проверка и rollback

Candidate проверяется отдельным GitHub gate, PostgreSQL migration/integration, full pytest и Render smoke `page 0 → page 1 → page 0`. Application rollback не очищает vacancy cache. Revision `0007` additive; controlled downgrade до `0006` — только после verified backup и развертывания совместимого старого кода.
