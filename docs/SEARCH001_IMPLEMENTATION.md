# AI Career Agent — SEARCH-001: единый контракт вакансии и нормализация данных

| Поле | Значение |
|---|---|
| Документ | SEARCH001_IMPLEMENTATION |
| Версия | 1.0 |
| Дата | 08 августа 2026 |
| Пакет | SEARCH-001 |
| Статус | НУЖНА ПРОВЕРКА |
| Рабочая основа | `ai-career-agent-site-main (11).zip` |
| Результирующий архив | `ai-career-agent-site-main-21-search-001-vacancy-contract-v1.4.5.zip` |
| Alembic revision | `20260808_0005` |
| Связанный план | PLAN_CURRENT 1.4.5 |

## 1. Контрольный статус

Код, миграция, local tests и документация готовы. Пакет остаётся **НУЖНА ПРОВЕРКА** до GitHub Actions с PostgreSQL и Render smoke.

## 2. Цель и границы

SEARCH-001 создаёт единую provider-to-application boundary для HH, SuperJob, Reed и Trudvsem. Пакет нормализует значения и типы, но не объединяет похожие вакансии между источниками — это SEARCH-002.

Не входят: fuzzy dedup, глобальный total/pagination, редизайн карточек, admin source center и AI matching.

## 3. Реализованный contract

`domain/vacancy_contract.py` содержит:

```text
NormalizedVacancy
WorkFormat
EmploymentCode
ExperienceCode
CONTRACT_VERSION = 1
```

Canonical values:

| Поле | Допустимые значения |
|---|---|
| work_format | remote, hybrid, onsite, field, fly_in_fly_out, unknown |
| employment_code | full, part, project, temporary, probation, volunteer, shift, side_job, unknown |
| experience_code | no_experience, between_1_and_3, between_3_and_6, more_than_6, unknown |
| source_status | active, closed |

Provider display labels сохраняются отдельно. `unknown` является нормальным значением и не заменяется догадкой.

## 4. Центральная нормализация

`services/vacancy_normalizer.py` централизует:

- HTML/entity/whitespace cleanup;
- currency aliases `RUR -> RUB`, `BYR -> BYN` и uppercase;
- salary parsing, invalid/zero/negative -> `None`, range ordering;
- epoch/ISO timestamps -> UTC ISO-8601 `Z`;
- provider-specific structured mappings;
- source status/lifecycle;
- deterministic contract serialization.

Adapters `normalize_hh_vacancy`, `normalize_reed_vacancy`, `normalize_superjob_vacancy`, `normalize_trudvsem_vacancy` возвращают один тип.

## 5. Persistence и migration 0005

Migration `20260808_0005_vacancy_normalization_contract.py` добавляет nullable canonical columns в `vacancies` и `vacancy_source_records`:

```text
work_format
employment_code
experience_code
```

Добавлены индексы. Backfill консервативный: только legacy `remote=true` становится `remote`; `remote=false` не превращается автоматически в onsite. Downgrade удаляет только новые indexes/columns.

`VacancyStore` нормализует mapping перед записью. `VacancyRepository` сохраняет canonical codes в canonical/source rows и фильтрует новые rows exact-code expressions. Legacy textual fallback используется только при `NULL` canonical field.

## 6. Search и presentation

`services/search_filters.py` применяет одну policy к cached и direct-provider results:

- keyword/region;
- exact work_format/employment/experience;
- normalized currency/salary;
- publication period;
- active lifecycle.

`app.py` выполняет common filter после aggregation. `vacancy_presenter.py` выдаёт consistent labels и отдельный `work_format_display`, сохраняя raw provider labels как fallback.

## 7. Изменённые файлы

```text
.github/workflows/ci.yml
app.py
database.py
domain/__init__.py
domain/entities.py
domain/vacancy_contract.py
models/vacancy.py
repositories/vacancies.py
services/hh_provider.py
services/reed_provider.py
services/search_filters.py
services/superjob_provider.py
services/trudvsem_provider.py
services/vacancy_normalizer.py
services/vacancy_presenter.py
services/vacancy_store.py
migrations/versions/20260808_0005_vacancy_normalization_contract.py
tests/test_search_normalization.py
repository/canonical documentation files
```

## 8. Влияние на сайт и совместимость

Визуальный layout, routes и OAuth/PDF flows не меняются. Existing Trudvsem cache остаётся доступным. New/updated rows получают canonical codes; legacy rows нормализуются при чтении и поддерживаются DB fallback.

Пользовательский результат: одинаковое поведение remote/hybrid/onsite, employment, experience, salary/currency и dates между источниками. Неизвестное значение не маскируется ложным фильтром.

## 9. Локальные доказательства

```text
focused SEARCH-001 tests: 29 passed
full available pytest: 139 passed, 6 skipped
SQLite upgrade to 20260808_0005: passed
alembic current/check: passed
SQLite downgrade 0005 -> 0004 -> 0005: passed
workflow YAML parse: passed
compileall: passed
```

Локальные skips относятся к Flask/Psycopg/PostgreSQL integration scenarios, которые запускаются GitHub Actions.

## 10. Ограничения и риски

- Provider totals остаются source-specific до SEARCH-003.
- Raw labels могут отличаться по языку и полноте.
- Legacy textual fallback временный и удаляется только после refresh/backfill policy.
- Canonical mapping консервативен; `unknown` предпочтительнее ложной классификации.
- Cross-source duplicates не склеиваются в этом пакете.

## 11. Rollback

1. Откатить application commit.
2. Оставить additive columns `0005` — старый код их игнорирует.
3. Downgrade до `0004` выполнять только после verified backup и после развёртывания старого кода.
4. Не удалять vacancy cache.

## 12. Следующее действие

Создать отдельную ветку SEARCH-001, получить полностью зелёный CI, merge и проверить Render revision `20260808_0005` и multi-source search. После подтверждения начать SEARCH-002.

## 13. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 08.08.2026 | Реализован SEARCH-001 candidate: typed contract, central normalizer, migration 0005, canonical filters и tests |
