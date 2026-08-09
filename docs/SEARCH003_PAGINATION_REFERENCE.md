# AI Career Agent — справочник пагинации SEARCH-003

| Поле | Значение |
|---|---|
| Документ | SEARCH003_PAGINATION_REFERENCE |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | CANDIDATE REFERENCE |
| Pipeline version | `1` |

## 1. Контрольный статус

Документ фиксирует contract snapshot pagination. Изменение полей, fingerprint или ordinal policy требует version bump и regression tests.

## 2. Search result contract

```text
snapshot_id
page
page_size
items[]
has_next
provider_reported_total
known_unique_total
total_is_exact
bounded
committed_count
late_arrival_count
source_results{}
deduplication_stats{}
snapshot_age_seconds
created
replaced
```

## 3. Fingerprint

SHA-256 строится из:

```text
pipeline_version
canonical filter dataclass
sorted selected source keys
page_size
```

В таблице не сохраняются raw keyword, region или salary. Fingerprint не является security token.

## 4. Stable identity и ordinal

Candidate identity:

```text
sha256(source + external_id/url/fallback)
```

Deduplicated stable key:

```text
sha256(sorted source identities))
```

После показа страницы её items входят в committed prefix. Existing committed ordinal не меняется. Новая source publication может обновить содержимое multi-source card, но не переносит её на другую страницу.

## 5. Sort policy

| Sort code | Primary order | Tie-breakers |
|---|---|---|
| `date` | published desc | title, company, source priority, source, external ID, stable hash |
| `salary_desc` | known salary desc | published desc + common tie-breakers |
| `salary_asc` | known salary asc | published desc + common tie-breakers |
| `relevance` | provider page/position rank | published desc + common tie-breakers |

Unknown salary всегда после known salary.

## 6. Total semantics

| Поле | Значение |
|---|---|
| `provider_reported_total` | Сумма текущих totals площадок до global filter/dedup; приблизительная |
| `known_unique_total` | Число materialized unique cards в snapshot |
| `total_is_exact` | Истина только при exhausted всех sources и отсутствии bounded cap |
| `bounded` | Достигнут max pages/candidates; exact total запрещён |

UI не должен печатать provider total как точное число уникальных вакансий.

## 7. Source state

Для каждого source:

```text
next_page
fetched_pages
fetched_items
reported_total
exhausted
error_count
last_error_type
last_fetched_at
```

Provider error не стирает кандидатов и items, ранее materialized в snapshot.

## 8. Progressive provider coverage

UI pagination использует `SEARCH_PAGE_SIZE=20`, независимо от provider-specific page size. Snapshot расширяется постепенно: один HTTP request по умолчанию выполняет максимум один concurrent provider round. Это предотвращает длинные цепочки внешних HTTP calls и большого числа PostgreSQL round-trips внутри одного пользовательского запроса.

Уже показанный ordinal range является committed prefix и не перемещается. Если поздно загруженная публикация имеет более высокий global sort priority, она не вставляется перед уже показанными карточками, а остаётся в uncommitted tail. `late_arrival_count` делает такое событие наблюдаемым.

Следующая страница может потребовать новый provider round; источники, у которых уже достаточно materialized candidates для этой границы, повторно не запрашиваются без необходимости.

## 9. TTL и limits

Default TTL — 30 минут. Touch продлевает TTL активного/complete snapshot при навигации. Cleanup каскадно удаляет только snapshot tables. Candidate/page limits запрещают неограниченный scan.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Зафиксирован SEARCH-003 result/fingerprint/sort/total/source-state contract. |
