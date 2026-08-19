# AI Career Agent — runbook PROF-003

| Поле | Значение |
|---|---|
| Документ | PROF003_RUNBOOK |
| Пакет | PROF-003 |
| Версия | 1.2 |
| Дата | 13 августа 2026 |
| Статус | ВЫПОЛНЕНО |

## 1. Назначение

Runbook описывает safe deploy и production verification серверных resume drafts/versions. Не публиковать answers/messages, image bytes, asset IDs, PDF hashes/filenames, cookies, session data или database credentials.

## 2. Pre-deploy

1. Подтвердить baseline GitHub ZIP comment `427b2726edd078993a3c26985e17713cf2e76c9e`.
2. Проверить `app.py`, WSGI `app:app`, `database.CURRENT_REVISION=20260812_0012`.
3. Убедиться, что `infra/vps/.env.example` есть, а `.env`, DB/dumps/backups/caches/bytecode отсутствуют.
4. Проверить migration upgrade/downgrade и backup inventory.
5. Новых Render environment variables нет.

## 3. GitHub gate

Обязательные steps:

```text
Verify PROF-003 server resume draft and version controls
Verify PROF-002 resume import review controls
Verify PROF-001 structured career profile controls
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify AUTH-001 / AUTH-002 regressions
Verify PostgreSQL encrypted backup and restore
Run tests
Docker/Compose runtime smoke
```

При любом failure merge запрещён.

## 4. Deploy

Start Command не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После `Live` проверить `/health/ready`: current/expected `20260812_0012`, persistent PostgreSQL, `status=ok`.

## 5. Основной E2E

1. Войти в verified account A.
2. Открыть `/resumes`, создать blank draft и отдельный draft из profile.
3. Изменить несколько полей; дождаться статуса server save.
4. Обновить страницу — state и revision сохраняются.
5. Войти в A в другом browser/device — открыть тот же draft и сравнить state.
6. Очистить legacy localStorage — server state остаётся.
7. Загрузить photo/logo; проверить после relogin.
8. Нажать «Сохранить версию» — version 1.
9. Изменить draft и создать version 2.
10. Открыть version 1 read-only; restore version 1 — current state меняется и появляется новая immutable version.
11. Повторить checkpoint без material change — duplicate version не появляется.

## 6. Concurrency

1. Открыть один draft в двух независимых сессиях на одной revision.
2. Сохранить session A.
3. Сохранить stale session B.
4. Ожидать `409`; изменения A не потеряны.

## 7. Asset isolation

- User B не открывает asset A.
- Asset одного draft нельзя присвоить другому draft.
- Фото PNG/JPG/WebP и эмблема PNG/JPG/WebP/GIF/ICO с валидной сигнатурой работают.
- Wrong signature/unsupported MIME/>2 MiB fail safely.

## 8. Export parity

1. Сохранить current state.
2. Запустить PDF export.
3. Сравнить страницы/текст preview и PDF.
4. Проверить history: export использует exact immutable version.
5. Повторный export без изменения может использовать ту же version, но создаёт отдельную export metadata row.
6. Убедиться, что server не выдаёт endpoint для скачивания stored PDF binary.

## 9. Delete и restart

- Создать test draft с versions/assets/export metadata.
- Удалить его; все зависимые rows исчезают, другие drafts остаются.
- Создать persistent draft; выполнить Render restart; current state/history/assets сохраняются.

## 10. Mobile и regression

На телефоне проверить library/builder/autosave/checkpoint/history/restore/image/export controls. Затем проверить `/profile`, PROF-002 import, `/dashboard`, login/logout, HH/SuperJob, `/vacancies`, ordinary search и `/health/ready`.

## 11. Observability и privacy

Разрешены events/fields:

```text
resume_draft_created/renamed/deleted
draft_revision, completion_percent, changed
resume_version, reason, created
asset_kind, asset_bytes
page_count, pdf_bytes, version_created
```

Запрещены answers/messages, full state/snapshot, asset bytes, filenames/hashes, owner ID, cookies/session token.

## 12. Rollback

1. Остановить new draft writes.
2. Сделать verified backup.
3. Application revert может оставить `0012`.
4. Downgrade `0012 -> 0011` удаляет всю PROF-003 data; выполнять только в maintenance window после explicit decision.

## 13. Текущий production gate

Уже подтверждены green CI, Render `0012`, drafts/autosave/cross-device, versions/no-op/read-only/restore, stale conflict, direct-edit r2, iPhone photo r3, university logo, PDF parity r4, owner isolation и restart persistence.

Финально подтверждено:

```text
/profile + PROF-002 import
/dashboard + login/logout
HH/SuperJob state
/vacancies + ordinary search
/health/ready = 0012
Render Logs privacy/error review
```

PROF-003 переведён в ВЫПОЛНЕНО; начинается PRIV-001.

## 14. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Создан deploy/autosave/history/assets/export/rollback runbook PROF-003. |
| 1.1 | 13.08.2026 | Recorded green CI/Render `0012`, production E2E/hotfix r1-r4/restart evidence; final regression/log review isolated as remaining gate. |
| 1.2 | 13.08.2026 | Final regression `/profile`/PROF-002/`/dashboard`/AUTH/OAuth/`/vacancies`, readiness `0012` and Render log privacy/error review confirmed; PROF-003 COMPLETE, PRIV-001 next. |
