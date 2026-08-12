# AI Career Agent — runbook PROF-001

| Поле | Значение |
|---|---|
| Документ | PROF001_RUNBOOK |
| Пакет | PROF-001 |
| Версия | 1.1 |
| Дата | 12 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Назначение

Runbook описывает безопасный branch/PR deploy и production verification structured owner profile. Не публиковать profile facts, cookies, session tokens, database credentials or private contact data in screenshots/log excerpts.

## 2. Pre-branch

1. Подтвердить baseline `ai-career-agent-site-main (14).zip` / current GitHub main.
2. Проверить WSGI `app:app`; `app_fixed.py` отсутствует.
3. Проверить `database.CURRENT_REVISION=20260811_0010`.
4. Убедиться, что ZIP не содержит `.env`, DB/dumps/backups, caches, bytecode, virtualenv or secrets.
5. Для hotfix использовать отдельную branch, например `prof-001-partial-profile-hotfix-v1.4.21`.

## 3. Pull Request gate

Обязательные steps:

```text
Verify PROF-001 structured career profile controls
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify AUTH-001 / AUTH-002 / SEC-001 regressions
Verify PostgreSQL encrypted backup and restore
Run tests
Docker/Compose runtime smoke
```

Не merge при любом red step.

## 3.1 Hotfix gate after production partial-save defect

Перед продолжением E2E обязательно подтвердить новый regression: форма с headline/target role и визуально пустыми repeatable rows (`employment_current=0`, `skill/language level=unspecified`) сохраняется как version 1 без требования company/position/skill/language. Новой migration нет; `/health/ready` остаётся на `20260811_0010`.

## 4. Deploy

Start Command не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После Live проверить `/health/ready` на `current=expected=20260811_0010`, persistent PostgreSQL, `migrations.ok=true`, `status=ok`.

## 5. Positive E2E

Использовать verified first-party account A.

1. `/dashboard` → Карьерный профиль → Создать профиль.
2. Сохранить только headline и одну target role. Ожидается version 1 и incomplete completion below 100.
3. Logout/login; профиль и version 1 сохраняются.
4. Добавить contact, skill, employment and salary. Ожидается version 2.
5. Открыть history и version 1: old facts unchanged, page read-only.
6. Повторно сохранить без изменения: history остаётся 2 versions.
7. Reload and mobile navigation/profile editor remain usable.

## 6. Owner isolation E2E

1. В account B открыть `/profile`: он должен иметь собственный empty state.
2. Attempt direct `/profile/history/1`: если version 1 принадлежит account A, ожидается `404`.
3. Save B profile; A facts must not appear.
4. Return to A; A current/history unchanged.

Не включать contact data A в screenshot B.

## 7. Concurrency E2E

1. Открыть `/profile/edit` A в обычной и private browser tabs на одной version.
2. В первой вкладке изменить headline and save: version increments.
3. Во второй вкладке попытаться save stale form.
4. Ожидается safe conflict message/`409`; первая новая version remains intact.
5. Refresh stale editor before continuing.

## 8. Restart persistence

После profile/history creation выполнить Render restart/redeploy without code change. Проверить current facts, completion, history and version snapshots after login.

## 9. Security and logs

Проверить:

- unauthenticated profile routes redirect to login;
- POST missing CSRF returns 400;
- invalid facts return bounded 400, not traceback;
- responses use `Cache-Control: no-store`;
- logs may contain `career_profile_saved`, `changed`, version and completion only;
- logs must not contain headline, summary, contacts, employment, user ID or snapshot JSON.

## 10. Regression

Проверить `/dashboard`, first-party login/logout, sessions, HH/SJ cards, `/vacancies` and ordinary search. `/health/ready` remains green.

## 11. Rollback

1. Stop editing and revert application commit.
2. Keep revision `0010` to preserve profile data.
3. Previous application ignores new tables.
4. Downgrade `0010 -> 0009` only before real profile data or after verified backup and explicit decision.
5. Do not modify User/AuthSession/OAuth/Search/Sync rows.

## 12. Exclusions

No resume import, AI population, public profile, version restore, autosave, export/delete/retention or external provider calls.

## 13. Закрытие

Close only after CI, Render, owner isolation, version/no-op/stale conflict, restart persistence and regression are confirmed. Then publish PROF-001 COMPLETE docs and make PROF-002 next.

## 14. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | Created branch/deploy/owner/version/concurrency/restart/security/rollback runbook. |
