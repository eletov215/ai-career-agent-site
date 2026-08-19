# AI Career Agent — реализация PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_IMPLEMENTATION |
| Пакет | PRIV-001 |
| Версия | 1.1 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Рабочая основа | GitHub main после PROF-003 COMPLETE / hotfix r4 |
| Production revision | `20260812_0012` |
| Candidate revision | `20260813_0013` |

## 1. Контрольный статус

PROF-003 закрыт после final regression/log review. PRIV-001 candidate реализован локально и готов к feature-branch PR. До полного GitHub CI, Render migration `0013` и destructive production E2E статус остаётся НУЖНА ПРОВЕРКА.

## 2. Цель и границы

Цель — дать first-party User работающие технические средства получить копию поддерживаемых данных, удалить аккаунт и применить прозрачную retention baseline до подключения публичного AI-контура.

В scope:

- readable owner export;
- current-password + exact-phrase account deletion;
- local HH/SuperJob credential cleanup;
- cascade profile/resume/session/token cleanup;
- identifier-free privacy audit;
- technical retention service, CLI and worker;
- UI, migration, backup inventory, tests and CI gate.

Не входят: юридическая квалификация/consent wording (`LEGAL-001`), remote provider-side OAuth grant revoke, data-portability schema guarantee для сторонних систем, asynchronous large-export queue, external object storage deletion API, billing data или будущая AI usage history.

## 3. Export contract

`POST /privacy-center/export` требует active first-party session и CSRF. Service собирает owner-scoped snapshot и возвращает ZIP:

```text
AI_Career_Agent_Data_Export_<timestamp>.zip
  manifest.json
  data.json
  assets/<draft>/<kind>-<asset-id>.<ext>
```

`data.json` включает account metadata, auth session/token metadata без hashes, OAuth connection identity/profile без access/refresh tokens, current career profile + immutable versions, resume drafts/versions/export metadata/assets metadata. Original owned image bytes включаются отдельными files. Server-side PDF binary отсутствует в продукте и поэтому не может быть экспортирован.

Намеренно исключены password hash, auth/session/token hashes, user-agent hash, OAuth access token, refresh token, browser OAuth state и любые server secrets.

## 4. Account deletion

`POST /privacy-center/delete-account` требует одновременно:

1. active authenticated User;
2. valid CSRF;
3. точную фразу `УДАЛИТЬ АККАУНТ`;
4. текущий password.

После успешной проверки repository блокирует owner row на PostgreSQL, считает только aggregate dependency counts, удаляет legacy provider mirrors, затем удаляет `User`. FK cascade удаляет auth sessions/tokens, unified OAuth connections, CareerProfile/versions и ResumeDraft/versions/assets/exports. Browser session очищается. Второй User не затрагивается.

Удаление является необратимым пользовательским действием. Восстановление возможно только из заранее созданного verified backup и требует отдельного operational/legal решения.

## 5. OAuth boundary

PRIV-001 гарантирует удаление локальных encrypted HH/SuperJob credentials из unified `oauth_connections` и legacy `hh_accounts`/`accounts` mirrors. Пакет не заявляет remote provider-side OAuth grant revoke: соответствующие provider revoke API не встроены и должны быть отдельным verified integration при необходимости.

## 6. Retention baseline

| Категория | Candidate default | Действие |
|---|---:|---|
| Pending unverified account | 30 дней | удалить stale pending User cascade |
| Expired/revoked auth session/token | 30 дней после expiry/revoke/consume | удалить auth artifact |
| Identifier-free privacy audit | 180 дней | удалить old audit row |
| Active profile/resume/OAuth data | до explicit account deletion | cleanup job не удаляет active owner data |
| Cleanup cadence | 24 часа | periodic worker; minimum config 1 час |

Эти сроки — technical baseline, а не юридическое обещание. Финальная privacy/legal policy фиксируется `LEGAL-001` до публичного коммерческого запуска.

## 7. Audit and logging

Migration `20260813_0013` создаёт `privacy_audit_events` только с `event_type`, bounded aggregate `counts_json`, timestamp и random row id. Нет FK/User ID/email/provider identity/filename/hash/content.

Allowed logs: event name + aggregate counts. Forbidden: exported JSON, resume/profile fields, asset bytes/IDs, email, user ID, deletion password, session/token/OAuth credentials.

## 8. Влияние на код и сайт

Ключевые новые файлы:

```text
models/privacy.py
repositories/privacy.py
services/privacy.py
routes/privacy_controls.py
scripts/cleanup_privacy.py
scripts/privacy_cleanup_worker.py
templates/privacy/center.html
templates/privacy/deleted.html
templates/privacy/not_found.html
migrations/versions/20260813_0013_privacy_controls.py
tests/test_priv001_migration.py
tests/test_privacy_service.py
tests/test_privacy_routes.py
```

Обновлены `app.py`, `config.py`, `database.py`, storage/auth service, backup inventory, runtime supervisor, Compose/Render/VPS manifests, navbar/dashboard/privacy page/styles, tests and CI.

На сайте появляется «Мои данные». Export и delete работают из first-party account; destructive form визуально отделена и требует повторного подтверждения.

## 9. Migration 20260813_0013

Additive migration создаёт только `privacy_audit_events` и два индекса. Existing User/Auth/OAuth/Profile/Resume tables не изменяются. Downgrade `0013 -> 0012` удаляет только audit table и не восстанавливает уже удалённые accounts.

## 10. Проверки

Local evidence:

```text
compileall                                      PASSED
focused PRIV/config/infra/architecture tests    86 passed, 1 expected local skip
SQLite clean upgrade to 0013                    PASSED
0013 -> 0012 -> 0013 round-trip                 PASSED
alembic check                                   PASSED
Jinja parse 28 templates                        PASSED
repository hygiene                              PASSED
infra manifest                                  PASSED
document structure                              PASSED
```

Flask route test в текущей isolated local runtime пропущен только потому, что Flask package отсутствует; GitHub workflow устанавливает production/dev requirements и обязан выполнить route test.

## 11. Ограничения и риски

- Synchronous ZIP export работает в web process и рассчитан на текущий bounded staging volume; при больших datasets потребуется streaming/background export.
- PostgreSQL BLOB resume assets входят в export и увеличивают memory size.
- Remote provider revoke отсутствует.
- Retention defaults должны пройти `LEGAL-001`.
- In-memory rate limit остаётся staging limitation до multi-replica shared store.

## 12. Rollback

Application revert совместим с additive `0013`. Controlled schema downgrade удаляет только privacy audit rows. Нельзя обещать rollback ранее выполненного account deletion; для такого восстановления нужен verified backup.

## 13. Следующее действие

Feature branch `priv-001-candidate-v1.4.27` -> PR -> full green CI -> merge -> Render `0013` -> throwaway-account export/delete/restart/log E2E.

## 14. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Implemented owner export, confirmed deletion, local OAuth/token cleanup, technical retention worker, identifier-free audit, migration `0013`, UI/tests/CI gate. |

## Hardened candidate v1.4.28

Повторный privacy/security аудит перед внешней проверкой усилил candidate: экспорт требует повторного текущего пароля и формируется как согласованный PostgreSQL snapshot; добавлены raw/archive size bounds, SpooledTemporaryFile, safe ZIP entry paths, OAuth profile sanitization и fail-closed owner/draft asset integrity. Account deletion повторно сверяет password hash под User row lock и использует единый lock order для Auth/OAuth rows. Retention cleanup получил bounded batches, orphan ResumeAsset cleanup (7d, только без current/history references), cross-process worker lock/heartbeat и индекс `idx_resume_assets_created`. Backup copies не переписываются account deletion; remote provider-side OAuth revoke не заявляется. Candidate schema остаётся `20260813_0013`; production до merge остаётся `20260812_0012`.
