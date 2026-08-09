# AI Career Agent — доменная модель

## 1. Основные агрегаты

```text
User 1 ── * OAuthConnection
Vacancy 1 ── * VacancySourceRecord
SyncRun / SyncWorker / SyncCheckpoint
SearchSnapshot 1 ── * SourceState / Candidate / Item
```

`Vacancy` и `VacancySourceRecord` — долговечный canonical/source cache. `SearchSnapshot*` — короткоживущий анонимный aggregate для стабильной пагинации; эти контуры намеренно разделены.

## 2. SEARCH-001 contract

`NormalizedVacancy` фиксирует canonical `work_format`, `employment_code`, `experience_code`, salary/currency, UTC dates и lifecycle. Unknown не заменяется догадкой.

## 3. SEARCH-002 grouping

Conservative dedup сохраняет все source records. Same-provider разные external IDs не объединяются. Cross-source merge требует hard gates/complete-link evidence и может быть обратимо разделён.

## 4. SEARCH-003 snapshot records

### SearchSnapshot

Хранит fingerprint, selected sources, sort/page size, aggregate counters, exact/bounded status, lease, TTL и committed prefix. Raw query text не хранится.

### SearchSnapshotSource

Per-provider cursor/state: `next_page`, fetched pages/items, reported total, `exhausted`, `bounded`, error count/type и last fetched time.

### SearchSnapshotCandidate

Bounded normalized provider publication до global dedup. Identity предпочитает external ID/URL; anonymous fallback включает provider page/position, поэтому разные anonymous rows не перезаписываются.

### SearchSnapshotItem

Deduplicated card с постоянным ordinal, stable source-key set и safe JSON payload. Existing committed ordinal не меняется; поздние arrivals добавляются после committed prefix.

## 5. Coverage invariant

Для page `N` каждый non-terminal source должен покрыть required depth accepted identities (`(N+1)*page_size + buffer`) либо стать exhausted/bounded. Это предотвращает commit global boundary только за счёт большого результата одной площадки.

## 6. Lifecycle

Snapshot создаётся/расширяется bounded rounds, touch продлевает TTL, expired rows удаляются каскадно. Cleanup не затрагивает canonical vacancy cache.
