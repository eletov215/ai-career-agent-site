# AI Career Agent — SEARCH-001: runbook проверки и rollout

| Поле | Значение |
|---|---|
| Документ | SEARCH001_RUNBOOK |
| Версия | 1.0 |
| Дата | 08 августа 2026 |
| Пакет | SEARCH-001 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Candidate revision | `20260808_0005` |
| Связанный план | PLAN_CURRENT 1.4.5 |

## 1. Контрольный статус

Runbook предназначен для candidate SEARCH-001. Merge разрешён только после полностью зелёного GitHub Actions.

## 2. Подготовка ветки

1. Создать ветку `search-001-vacancy-contract` от актуального `main`.
2. Загрузить полный ZIP через GitHub Desktop/Git, сохранив `.github`, `.dockerignore`, `.gitignore`, `infra/vps/.env.example`.
3. Убедиться, что migration `20260808_0005` и новый CI step присутствуют.
4. Commit:

```text
search: add typed vacancy contract and canonical normalization
```

## 3. Проверка GitHub Actions

Открыть Actions и дождаться зелёного job `Python tests`. Особое внимание:

```text
Verify SEARCH-001 vacancy contract and normalization controls
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify PostgreSQL encrypted backup and restore
Build INFRA-001 container targets
Smoke-test INFRA-001 runtime image
Run tests
```

При красном шаге не merge и не re-run старый commit после code fix — нужен новый commit.

## 4. Merge и Render

После зелёного CI:

1. Merge Pull Request в `main`.
2. Дождаться повторного CI для `main`.
3. Дождаться Render deploy `Live`.
4. Start Command не менять:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

## 5. Health/migration smoke

Открыть:

```text
/health/live
/health/ready
/health
```

Ожидается `200`, PostgreSQL persistent и revision `20260808_0005`.

## 6. Multi-source search smoke

На основном vacancies route выполнить:

1. базовый поиск без дополнительных фильтров;
2. keyword + region;
3. remote;
4. hybrid;
5. onsite;
6. employment full/part/project;
7. experience brackets;
8. currency + salary threshold;
9. period.

Проверить: страница отвечает без 500; карточки сохраняют source/company/title/url; source failure не ломает остальные результаты; unknown не выдаётся как ложный match.

## 7. Database/compatibility checks

- существующий Trudvsem cache не обнулился;
- refreshed rows получают canonical fields;
- legacy rows без codes остаются видимыми;
- migration повторный запуск безопасен;
- worker SYNC-001/002 остаётся жив.

## 8. Rollback

1. Остановить merge/deploy при красном CI.
2. При production regression redeploy предыдущий commit.
3. Оставить additive `0005` columns.
4. Downgrade до `0004` только после backup и только при явной необходимости.
5. Не очищать vacancy data.

## 9. Завершение

После успешной проверки обновить status SEARCH-001 на ВЫПОЛНЕНО, PLAN_CURRENT на следующую PATCH-версию и подготовить SEARCH-002.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 08.08.2026 | Создан rollout/verification runbook SEARCH-001 |
