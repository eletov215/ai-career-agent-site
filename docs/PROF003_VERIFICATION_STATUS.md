# AI Career Agent — статус проверки PROF-003

| Поле | Значение |
|---|---|
| Документ | PROF003_VERIFICATION_STATUS |
| Пакет | PROF-003 |
| Версия | 1.0 |
| Дата | 13 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Production baseline | `20260812_0011` |
| Candidate schema | `20260812_0012` |

## 1. Контрольный статус

Код candidate готов локально, но PROF-003 нельзя переводить в ВЫПОЛНЕНО до green Pull Request CI, Render migration/readiness `0012` и production E2E.

## 2. Подтверждённая рабочая основа

Загруженный GitHub ZIP содержит функциональный код PROF-002 COMPLETE + upload-limit hotfix r2. Его ZIP comment — `427b2726edd078993a3c26985e17713cf2e76c9e`, SHA-256 — `ddd4d61f0afbf3351c0623506fc9e35aca757e0536716b4015349abc96e40864`. Функциональная часть совпала с контрольным PROF-002 complete snapshot; 11 repository docs были позади canonical v1.4.24 и синхронизированы до начала PROF-003.

## 3. Локальные доказательства

```text
split full available pytest                 252 passed, 11 skipped
focused PROF-003 migration/service/routes   15 passed, 1 skipped
compileall                                  passed
Jinja parse                                 25 templates passed
JavaScript syntax                           passed
SQLite clean upgrade                        0012 passed
SQLite downgrade/re-upgrade                 0012 -> 0011 -> 0012 passed
Alembic check                               passed
repository hygiene / infra manifest         passed
```

Локальные skips относятся к отсутствующим Flask/Psycopg/PostgreSQL runtime-зависимостям; соответствующие route/PostgreSQL проверки входят в обязательный Pull Request CI.

## 4. Автоматизированная матрица

| Проверка | Ожидаемый результат | Статус |
|---|---|---|
| migration 0011 -> 0012 | четыре таблицы/constraints/indexes | ЛОКАЛЬНО PASSED |
| downgrade 0012 -> 0011 | удаляются только PROF-003 tables | ЛОКАЛЬНО PASSED |
| draft validation/hash/no-op | bounded canonical state | ЛОКАЛЬНО PASSED |
| owner-scoped repository | чужой draft/version/asset недоступен | CI REQUIRED |
| stale revision | controlled `409`, no lost update | CI REQUIRED |
| checkpoint no duplicate | same hash не создаёт version spam | CI REQUIRED |
| restore | old snapshot -> new immutable version | CI REQUIRED |
| asset upload | MIME/signature/size/owner/draft checked | CI REQUIRED |
| export metadata | tied to exact immutable version | CI REQUIRED |
| PostgreSQL restart | draft/history/assets persist | PRODUCTION REQUIRED |
| preview/export parity | one locked state | PRODUCTION REQUIRED |

## 5. Positive production matrix

1. Создать blank draft и draft из PROF-001.
2. Ввести данные, дождаться server autosave.
3. Войти с другого устройства/приватной сессии — увидеть тот же state.
4. Очистить localStorage/cookies в одном browser, снова войти — state сохранён.
5. Загрузить photo/logo — они видны после relogin/restart.
6. Создать version 1, изменить material state, создать version 2.
7. Открыть version 1 read-only; restore создаёт следующую version.
8. Повторный no-op checkpoint не создаёт duplicate version.
9. Export создаёт/использует immutable version и metadata; PDF совпадает с preview.
10. Несколько resume drafts одного User независимы.

## 6. Negative production matrix

- Без login `/resumes` и `/resume-builder` redirect на login.
- User B получает `404` на draft/history/version/asset User A.
- Stale editor получает `409`, newer state сохраняется.
- Asset другого draft/User отклоняется.
- Unsupported/oversized/mismatched image fail closed.
- Oversized/unknown-state payload получает safe `400/413`.
- POST/PUT без CSRF получает `400`.
- Delete draft каскадно удаляет versions/assets/export metadata только владельца.
- Logs не содержат answers/messages/photo bytes/full snapshot/session token.

## 7. Render gate

После merge ожидается:

```text
status=ok
database.backend=postgresql
database.persistent=true
database.revision=20260812_0012
migrations.current_revision=20260812_0012
migrations.expected_revision=20260812_0012
migrations.ok=true
```

## 8. Security gate

- First-party User + active server-side AuthSession — единственная browser identity boundary.
- Все draft/version/asset/export reads owner-scoped.
- Autosave/checkpoint/export/restore требуют CSRF и expected revision.
- State и images bounded; PDF binary не принимается сервером.
- Logs разрешают только counts/result/revision/version/bytes metadata.

## 9. Ограничения

AI, public share, collaborative merge, server PDF binary storage, external object storage, account export/delete и retention не входят в acceptance criteria.

## 10. Rollback

Application revert совместим с `0012`. Downgrade `0012 -> 0011` удаляет PROF-003 data и допустим только после backup/explicit decision.

## 11. Решение о статусе

```text
PROF-003 — НУЖНА ПРОВЕРКА
Next after completion — PRIV-001
```

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Зафиксированы local evidence и обязательный CI/Render/E2E gate PROF-003. |
