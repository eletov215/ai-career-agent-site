# AI Career Agent — runbook PROF-002

| Поле | Значение |
|---|---|
| Документ | PROF002_RUNBOOK |
| Пакет | PROF-002 |
| Версия | 1.0 |
| Дата | 12 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Назначение

Runbook описывает безопасный deploy и production verification импорта PDF-резюме в подтверждённый PROF-001. Не публиковать PDF, filename, extracted text, contacts, signed token, cookies, session data или database credentials.

## 2. Pre-deploy

1. Подтвердить baseline commit `f5e513f0f992b20305fbef36851ef97576013c86`.
2. Убедиться, что ветка содержит только PROF-002 + DOC-001 изменения.
3. Проверить `app.py`, WSGI `app:app`, `database.CURRENT_REVISION=20260812_0011`.
4. Убедиться в отсутствии `.env`, DB/dumps/backups/caches/bytecode.
5. Новых Render environment variables нет.

## 3. GitHub gate

Обязательные steps:

```text
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

После Live проверить `/health/ready` на current/expected `20260812_0011`, persistent PostgreSQL и `status=ok`.

## 5. Основной E2E

1. Войти в verified first-party account A.
2. Открыть `/profile/import`.
3. Загрузить текстовый PDF с контактами, опытом, навыками, образованием и языками.
4. Убедиться, что открылся review, а `/profile` до confirm не изменился.
5. Проверить confidence, warnings, conflict copy и evidence excerpts.
6. Исправить минимум одно предложение и удалить минимум одно ошибочное.
7. Нажать `Подтвердить и сохранить`.
8. Проверить material version и source label `Импорт резюме` в history.
9. Historical page должна показывать aggregate provenance без filename/text.
10. Logout/login и restart сохраняют confirmed version.

## 6. Existing profile merge

1. В A создать/оставить подтверждённый headline/contact.
2. Загрузить PDF с другим headline/contact.
3. Review должен сохранить current value в форме и отдельно показать suggestion/conflict.
4. Без ручного изменения current scalar остаётся прежним.
5. После ручного выбора suggestion сохраняется именно выбранное пользователем значение.

## 7. Negative E2E

- Без login `/profile/import` недоступен.
- TXT, повреждённый PDF, scan-only PDF и over-limit document отклоняются без profile changes.
- Получить review token в A; попытаться confirm в B — safe failure.
- Получить review, затем изменить profile в другой вкладке; старый confirm — controlled `409`.
- Повторить confirm без CSRF — `400`.
- Истёкший review требует re-upload.

## 8. Observability и privacy

Разрешённые events:

```text
resume_import_review_prepared
resume_import_confirmed
```

Разрешённые поля: page_count, character_count, detected_section_count, conflict_count, changed, profile_version, completion_percent.

Запрещены: filename, raw text, source excerpts, contacts, proposed/confirmed payload, signed token, owner ID, cookies.

## 9. Regression

Проверить `/profile/edit`, history/no-op, owner isolation, `/dashboard`, login/logout, HH/SuperJob cards, `/vacancies`, ordinary search и `/health/ready`.

## 10. Rollback

1. Application revert.
2. Revision `0011` можно оставить.
3. Downgrade `0011 -> 0010` только в maintenance window; canonical profile data остаётся, audit source/provenance удаляется.
4. При privacy incident отозвать sessions и следовать SEC/OPS procedure.

## 11. Exclusions

OCR, DOC/DOCX, AI/LLM extraction, background jobs, persisted review drafts, autosave, provider import and auto-confirm не являются acceptance criteria.

## 12. Закрытие

Только после green CI, Render `0011`, positive/negative production E2E, restart persistence, mobile smoke и regression пакет переводится в `ВЫПОЛНЕНО`.

## 13. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 12.08.2026 | Создан deploy/import/review/privacy/rollback runbook PROF-002. |
