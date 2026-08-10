# AI Career Agent — статус проверки SEARCH-004

| Поле | Значение |
|---|---|
| Документ | SEARCH004_VERIFICATION_STATUS |
| Пакет | SEARCH-004 |
| Версия | 1.0 |
| Дата | 10 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Production schema | `20260809_0007` |

## 1. Контрольный статус

Код и локальные проверки готовы. Пакет остаётся НУЖНА ПРОВЕРКА до зелёного GitHub Actions и production route/source-state smoke.

## 2. Реализованные критерии

| Критерий | Состояние |
|---|---|
| `/vacancies` обслуживает unified search UI | Реализовано локально |
| `/vacancies/internal` permanent `308` redirect | Реализовано локально |
| Raw query/snapshot/page preservation | Покрыто route test |
| `Cache-Control: no-store` и `X-Robots-Tag: noindex` | Покрыто route test |
| Forms/pagination canonical URL | Реализовано и покрыто template/route tests |
| Safe source-state contract | 6 unit tests passed |
| Trudvsem marked cached/degraded | Покрыто unit tests |
| Unavailable provider excluded before search | Покрыто route test |
| Provider failure does not break page | Route regression prepared |
| No env/token/error leakage | Unit/route assertions prepared |
| GitHub Actions | ОЖИДАЕТСЯ |
| Render smoke | ОЖИДАЕТСЯ |

## 3. Локальные доказательства

```text
193 passed
6 skipped
```

Focused source-state suite:

```text
6 passed
```

Python compile и Jinja parse прошли.

## 4. Production checklist

1. `/health/ready` возвращает `status=ok` и revision `20260809_0007`.
2. `/vacancies` возвращает `200` и полный search UI.
3. `/vacancies/internal?search=1&source=hh&source=superjob&page=1&snapshot=<uuid>` возвращает `308` на `/vacancies` с теми же raw parameters.
4. Старый snapshot UUID после redirect не пересоздаётся только из-за route rename.
5. Navbar/home/footer links, forms и pagination ведут на `/vacancies`.
6. Работа России помечена как cached/degraded, а не live.
7. Отключённый provider имеет neutral `temporarily_unavailable`, отключённый checkbox и не вызывается.
8. Ошибка одного provider сохраняет результаты остальных и нейтральный warning.
9. Public HTML не раскрывает credentials, exception bodies или имена environment variables.

## 5. Ограничения и риски

Flask/Psycopg/PostgreSQL runtime scenarios не выполнены локально в изолированной среде; они остаются GitHub CI gate. Permanent method-preserving `308` уже включён; production smoke должен подтвердить сохранение query/snapshot/page.

## 6. Rollback

Application revert; migration отсутствует. Search snapshot tables и revision `0007` остаются без изменений.

## 7. Следующее действие

Загрузить code ZIP в отдельную branch и проверить dedicated CI step `Verify SEARCH-004 canonical route and source-state controls`.

## 8. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Candidate verification status после локальных tests. |
