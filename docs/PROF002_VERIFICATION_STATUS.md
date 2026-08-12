# AI Career Agent — статус проверки PROF-002

| Поле | Значение |
|---|---|
| Документ | PROF002_VERIFICATION_STATUS |
| Пакет | PROF-002 |
| Версия | 1.0 |
| Дата | 12 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Production revision | `20260811_0010` |
| Candidate revision | `20260812_0011` |

## 1. Контрольный статус

Код и локальные проверки PROF-002 готовы. Внешний GitHub/Render/production gate ещё не выполнен, поэтому пакет не переводится в `ВЫПОЛНЕНО`.

## 2. Подтверждённая рабочая основа

Загруженный `ai-career-agent-site-main (16).zip` полностью совпадает с предыдущим полным PROF-001 hotfix snapshot. ZIP comment содержит commit `f5e513f0f992b20305fbef36851ef97576013c86`. Это соответствует каноническому состоянию PROF-001 complete / production `0010`.

## 3. Автоматизированные доказательства

```text
full available pytest                     246 passed, 10 skipped
focused PROF-002/PROF-001/parser          15 passed
architecture/template/document subset     23 passed
compileall                                 passed
Jinja parse                               22 templates passed
SQLite upgrade 0000 -> 0011               passed
SQLite downgrade 0011 -> 0010             passed
SQLite re-upgrade 0010 -> 0011            passed
Alembic check                              passed
```

Ожидаемые local skips:

- Flask route tests — dependency устанавливается в CI;
- Psycopg/PostgreSQL integration — PostgreSQL 17 service существует в CI.

## 4. Positive matrix для внешней проверки

| Проверка | Ожидаемый результат | Статус |
|---|---|---|
| authenticated upload text PDF | открывается editable review | ОЖИДАЕТСЯ |
| upload без confirm | профиль/история не меняются | ОЖИДАЕТСЯ |
| корректировка предложений | форма сохраняет исправленные значения | ОЖИДАЕТСЯ |
| explicit confirm | создаётся material version с source `resume_import` | ОЖИДАЕТСЯ |
| existing confirmed scalar conflict | текущее значение не заменяется молча | ОЖИДАЕТСЯ |
| logout/login | подтверждённая версия сохраняется | ОЖИДАЕТСЯ |
| restart/redeploy | current facts и history/provenance сохраняются | ОЖИДАЕТСЯ |
| mobile review | upload/review/confirm доступны на телефоне | ОЖИДАЕТСЯ |

## 5. Negative matrix

| Проверка | Ожидаемый результат | Статус |
|---|---|---|
| без first-party session | redirect на login | ОЖИДАЕТСЯ |
| non-PDF / invalid signature | safe `400` | ОЖИДАЕТСЯ |
| image-only PDF | safe message, profile unchanged | ОЖИДАЕТСЯ |
| oversized/pages/text limits | safe `413/400` | ОЖИДАЕТСЯ |
| token другого User | safe `400`, no foreign save | ОЖИДАЕТСЯ |
| expired/tampered token | safe `400` | ОЖИДАЕТСЯ |
| profile changed after upload | controlled `409`, newer facts preserved | ОЖИДАЕТСЯ |
| confirm without CSRF | `400` | ОЖИДАЕТСЯ |
| logs | no filename/text/contacts/payload/token | ОЖИДАЕТСЯ |

## 6. Render gate

После merge ожидается:

```text
status=ok
database.backend=postgresql
database.persistent=true
database.revision=20260812_0011
migrations.current_revision=20260812_0011
migrations.expected_revision=20260812_0011
migrations.ok=true
auth.email_backend=gmail_api
oauth_configured=true
```

## 7. Security gate

- Upload и extracted text не persistence objects.
- Review token owner-bound через HMAC fingerprint, time-limited и без facts.
- Confirmation использует PROF-001 validation/version lock.
- Historical version source/provenance owner-scoped.
- Logs содержат только counts/outcome/version metadata.

## 8. Ограничения

OCR, DOCX, AI parsing, persisted draft, background import, provider resume import, auto-confirm and historical restore исключены.

## 9. Rollback

Application revert совместим с revision `0011`. Downgrade удаляет только audit provenance columns, а не profile snapshots.

## 10. Решение о статусе

```text
PROF-002 — НУЖНА ПРОВЕРКА
Next gate — green Pull Request CI + Render 0011 + production E2E
```

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 12.08.2026 | Зафиксированы local evidence, positive/negative matrix и обязательный external gate PROF-002. |
