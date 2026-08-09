# AI Career Agent — реализация SEARCH-002

| Поле | Значение |
|---|---|
| Документ | SEARCH002_IMPLEMENTATION |
| Пакет | SEARCH-002 — дедупликация между источниками |
| Версия | 1.0 |
| Дата | 09 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Основа кода | `ai-career-agent-site-main (12).zip` |
| Candidate revision | `20260809_0006` |
| Следующий gate | GitHub Actions и Render production smoke |

## 1. Контрольный статус

SEARCH-002 реализован поверх подтверждённого typed vacancy contract SEARCH-001. Код, additive migration, локальные tests и документация candidate готовы. Статус ВЫПОЛНЕНО не присваивается до зелёного GitHub Actions и production smoke на Render.

## 2. Цель и границы

Цель — не показывать одну и ту же вакансию несколько раз, если она опубликована на разных площадках, при этом:

- не склеивать похожие, но разные роли;
- не терять исходные provider IDs и URLs;
- хранить несколько `VacancySourceRecord` под одной canonical `Vacancy` только после доказанного совпадения;
- сохранять объяснение решения и делать grouping обратимым;
- не менять основной URL и визуальную концепцию выдачи;
- не решать global pagination/total — это SEARCH-003.

## 3. Реализация

### 3.1 Conservative deduplication service

Добавлен `services/vacancy_deduplication.py`:

- NFKC/casefold normalization title/company/location;
- aliases для русских/английских role tokens и удаление юридических форм компании;
- versioned `dedup_key` SHA-256 для строгого candidate lookup;
- hard gates по employer, title, seniority, location/work format, canonical employment/experience, currency/salary и publication date;
- осторожная `SequenceMatcher + Jaccard` similarity только после прохождения hard gates;
- complete-link grouping: кандидат обязан совпасть со всеми элементами группы;
- collapse повторов одного provider только при одинаковой source identity;
- deterministic primary card по completeness, recency и фиксированному source priority;
- bounded `deduplication.method/confidence/reasons` и стабильный `dedup_group_id`.

False negative намеренно предпочтительнее false positive.

### 3.2 Source preservation и безопасные ссылки

Каждая объединённая карточка сохраняет:

```text
source_records[]
sources[]
source_titles[]
source_count
duplicate_count
alternative_sources[]
deduplication{}
```

Provider URLs допускаются к отображению только при `http/https`, без embedded credentials и с ограниченной длиной. Primary action выбирает безопасную доступную ссылку.

### 3.3 Persistence boundary

Добавлена migration `20260809_0006_cross_source_dedup_keys.py`:

- nullable `dedup_key` и `dedup_version` в `vacancies`;
- nullable `dedup_key` и `dedup_version` в `vacancy_source_records`;
- non-unique indexes для candidate lookup;
- historical rows не backfill-ятся и остаются `NULL` до provider refresh.

`VacancyStore` вычисляет metadata на persistence boundary. `VacancyRepository`:

- связывает доказанные duplicates разных providers с одной canonical vacancy;
- сохраняет отдельные source rows;
- не объединяет разные external IDs одного provider;
- удаляет только orphan canonical row после reassignment;
- умеет отделить источник обратно в отдельную canonical vacancy, если обновлённая публикация перестала совпадать со всеми активными членами группы;
- после split перестраивает прежнюю canonical vacancy из оставшихся source rows.

### 3.4 Search и presentation

`app.py` выполняет dedup после canonical filters и до сортировки. В structured log пишутся только bounded counts без названий вакансий и provider payload.

`services/vacancy_presenter.py` формирует multi-source view model и стабильный save key. Шаблон показывает:

- stacked provider logos;
- корректную русскую форму числа площадок;
- раскрываемый список всех исходных публикаций;
- primary apply action без изменения существующего пользовательского пути.

## 4. Влияние на код и сайт

Изменены:

```text
app.py
database.py
domain/entities.py
models/vacancy.py
repositories/vacancies.py
services/vacancy_deduplication.py
services/vacancy_store.py
services/vacancy_presenter.py
migrations/versions/20260809_0006_cross_source_dedup_keys.py
templates/vacancies_unified.html
static/theme.css
tests/test_search_deduplication.py
tests/test_routes.py
tests/test_vacancy_presenter.py
.github/workflows/ci.yml
docs/
```

Пользовательское влияние:

- high-confidence дубли разных площадок становятся одной карточкой;
- все исходные публикации остаются доступными;
- неоднозначные пары остаются отдельными;
- filters и `/vacancies/internal` не меняются;
- provider total остаётся approximate до SEARCH-003;
- existing cache не очищается.

## 5. Проверки и доказательства

Локально пройдены:

```text
SEARCH-002 dedup/migration suite: 15 passed
presenter suite: 5 passed
provider/search normalization/filter suites: passed
repository/store/sync migration regressions: passed
Python compile: passed
SQLite migration 0005 -> 0006 -> 0005 -> 0006: passed
Alembic check: passed
Jinja template parse: passed
```

Flask route, Psycopg/PostgreSQL 17 и Docker scenarios должны быть подтверждены GitHub Actions.

## 6. Ограничения и риски

- Embeddings, AI matching и широкие fuzzy company aliases не применяются.
- Similarity работает только внутри текущего агрегированного набора; stable cross-page totals относятся к SEARCH-003.
- Historical rows не объединяются массовым backfill во время deploy.
- Реальный provider dataset может не содержать удобную duplicate pair в момент production smoke; positive/negative semantics тогда подтверждаются CI fixtures.
- Один provider с разными external IDs не объединяется даже при одинаковом тексте.

## 7. Rollback

1. Откатить application commit и выполнить redeploy.
2. Не очищать vacancy/source cache.
3. Additive columns revision `0006` могут остаться при application rollback.
4. Controlled downgrade до `0005` выполнять только после verified backup и только когда старый код уже развернут.
5. После rollback provider publications снова отображаются отдельно.

## 8. Следующее действие

1. Загрузить candidate в отдельную branch.
2. Получить полностью зелёный GitHub Actions, включая SEARCH-002 gate и PostgreSQL migration/integration.
3. Merge в `main`.
4. Проверить Render revision `20260809_0006`, readiness и multi-source positive/negative smoke.
5. После подтверждения закрыть SEARCH-002 и начать SEARCH-003.

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 09.08.2026 | Реализованы conservative cross-source grouping, reversible persistence metadata и multi-source card candidate. |
