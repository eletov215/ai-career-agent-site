# AI Career Agent — справочник дедупликации SEARCH-002

| Поле | Значение |
|---|---|
| Документ | SEARCH002_DEDUP_REFERENCE |
| Пакет | SEARCH-002 |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | CANDIDATE REFERENCE |
| Алгоритм | `SEARCH-002 dedup version 1` |

## 1. Контрольный статус

Справочник фиксирует правила, по которым публикации разных providers могут считаться одной вакансией. Он не заменяет tests и не разрешает расширять fuzzy thresholds без отдельного package review.

## 2. Входной contract

Алгоритм получает SEARCH-001 mapping:

```text
source, external_id, title, company, location
work_format, employment_code, experience_code
salary_from, salary_to, currency
published_at, url, description, requirements
source_status
```

Unknown остаётся unknown.

## 3. Strict candidate key

`dedup_key` строится только при наличии нормализованных title и employer:

```text
SHA-256(
  dedup_version |
  normalized_title |
  normalized_company |
  location_scope
)
```

Для `remote/hybrid` location scope становится distributed. Key не является unique constraint и используется только для быстрого candidate lookup. Финальное решение всегда повторно проходит hard gates.

## 4. Hard gates и similarity

| Признак | Правило |
|---|---|
| Provider | Разные external IDs одного provider не объединяются |
| Company | Exact normalized key или очень близкая token/sequence форма после удаления legal suffixes |
| Seniority | Известные signatures не конфликтуют |
| Location | Exact/compatible city; одинаковый distributed format допускает разные labels |
| Canonical codes | Известные work/employment/experience значения не конфликтуют |
| Publication date | Разница не более 45 дней |
| Salary | Валюта совместима, интервалы пересекаются или близки |
| Title | Exact normalized title или высокий token/sequence score |
| Generic title | Требует дополнительного description overlap и salary support |

## 5. Grouping

Используется complete-link:

```text
новый кандидат сравнивается со всеми членами группы
merge допускается только если совпали все пары
```

Это предотвращает цепочку `A≈B`, `B≈C`, но `A≠C`.

## 6. Same-provider identity

Повторы одной и той же provider publication схлопываются только по одинаковому:

```text
source + external_id
```

или одинаковому URL при отсутствии ID. Разные external IDs одного provider остаются отдельными.

## 7. Primary card и source list

Primary выбирается детерминированно:

1. completeness/quality;
2. publication recency;
3. fixed source priority;
4. source/external ID tie-breaker.

Все исходные публикации сохраняются в `source_records`; URLs проходят HTTP/HTTPS validation. Primary card не скрывает альтернативные площадки.

## 8. Explainability

Merged item содержит:

```text
dedup_group_id
dedup_key
dedup_version
source_records[]
sources[]
source_count
duplicate_count
is_cross_source_duplicate
deduplication.method
deduplication.confidence
deduplication.reasons
```

Public UI показывает площадки; internal score не используется как обещание пользователю.

## 9. Persistence и обратимость

Migration `20260809_0006` добавляет nullable metadata columns. Исторический backfill отсутствует. При refresh доказанная cross-source group получает одну canonical vacancy и несколько source rows.

Если обновлённый source перестаёт совпадать со всеми активными членами группы, repository создаёт отдельную canonical vacancy для этого source и перестраивает прежнюю canonical из оставшихся rows. Source rows не удаляются.

## 10. Ограничения и rollback

Company embeddings, semantic AI merge и global clusters не входят в version 1. Global pagination/total остаётся SEARCH-003. Rollback — application revert; additive schema `0006` может оставаться.

## 11. Следующее действие

Пороговые значения меняются только отдельным review с positive/negative fixtures и production evidence.

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Зафиксированы candidate key, hard gates, complete-link, explainability и reversible persistence. |
