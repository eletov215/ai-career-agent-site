# AI Career Agent — runbook SEARCH-004

| Поле | Значение |
|---|---|
| Документ | SEARCH004_RUNBOOK |
| Пакет | SEARCH-004 |
| Версия | 1.0 |
| Дата | 10 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ CANDIDATE RUNBOOK |

## 1. Контрольный статус

Runbook применяется к candidate SEARCH-004. Database revision не меняется.

## 2. Подготовка GitHub

Создать branch от актуального `main`:

```text
search-004-canonical-vacancies
```

Рекомендуемый commit:

```text
search: make vacancies route canonical and expose safe source states
```

## 3. CI

Обязательный step:

```text
Verify SEARCH-004 canonical route and source-state controls
```

Также должны оставаться зелёными SEARCH-001/002/003, SEC, OPS, SYNC, PostgreSQL, backup/restore и container smoke.

## 4. Render deploy

Start Command не менять:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Ожидаемая revision:

```text
20260809_0007
```

## 5. Route smoke

Проверить:

```text
GET /vacancies                         -> 200
GET /vacancies/internal               -> 308 Location: /vacancies
GET /vacancies/internal?<query>       -> 308 с тем же raw query
```

Для legacy response также проверить:

```text
Cache-Control: no-store, max-age=0
X-Robots-Tag: noindex
```

Старую SEARCH-003 ссылку проверить с repeated `source`, `snapshot` и `page`. После redirect должен сохраниться тот же UUID, а committed page не должна пересоздаваться только из-за route rename.

## 6. UI smoke

1. Открыть `/vacancies` без поиска.
2. Проверить source labels и semantic dots.
3. Выполнить HH + SuperJob search.
4. Выполнить search с Trudvsem.
5. Убедиться, что Trudvsem подписан как saved cache/degraded, а не live.
6. Выбрать временно недоступный provider: checkbox должен быть disabled либо provider должен быть исключён до запроса.
7. Public copy не должна содержать env variable, exception, traceback или provider body.
8. Pagination links остаются на `/vacancies`.

## 7. Failure smoke

При контролируемой ошибке одного provider общая страница возвращает `200`, показывает результаты других sources и neutral warning с названием площадки без traceback/body/token.

## 8. Rollback

Откатить application commit и redeploy. Database downgrade не выполнять. Проверить, что compatibility URL всё ещё доступен на протяжении rollback window.

## 9. Следующее действие

После green CI/Render smoke обновить canonical status до ВЫПОЛНЕНО. По обязательной последовательности PLAN_CURRENT следующим кодовым пакетом становится `AUTH-001`; SEARCH-005 остаётся после account/profile/privacy foundation.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Создан полный CI/Render/route/source-state runbook. |
