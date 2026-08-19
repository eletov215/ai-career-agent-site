# AI Career Agent — реализация PROF-003

| Поле | Значение |
|---|---|
| Документ | PROF003_IMPLEMENTATION |
| Пакет | PROF-003 |
| Версия | 1.2 |
| Дата | 13 августа 2026 |
| Статус | ВЫПОЛНЕНО |
| Рабочая основа | GitHub `main` после PROF-003 hotfix r4 |
| Production revision | `20260812_0012` |
| Schema revision | `20260812_0012` |

## 1. Контрольный статус

PROF-003 реализован и работает в production на revision `20260812_0012`. Green GitHub CI, основной owner/autosave/version/asset/export/mobile E2E и Render restart persistence подтверждены. В production были найдены и исправлены четыре hotfix-класса: structured logging r1, direct field edit r2, iOS/Safari photo upload r3, PDF university-logo/education parity r4. Финальный regression и Render log privacy/error review подтверждены пользователем; PROF-003 закрыт со статусом **ВЫПОЛНЕНО**.

## 2. Цель и границы

Цель — позволить пользователю продолжать работу над резюме после очистки браузера, на другом устройстве и после restart/redeploy, не превращая текст документа в canonical facts PROF-001.

В scope:

- несколько owner-scoped резюме одного first-party User;
- mutable current draft с `revision` и content hash;
- autosave API с stale-write protection;
- immutable version snapshot по явному checkpoint, export или restore;
- история и read-only просмотр версии;
- восстановление старой версии как новой immutable версии;
- server-side photo/university-logo assets;
- PDF export metadata, привязанная к immutable version;
- одноразовый перенос прежнего localStorage state на сервер;
- создание нового черновика из подтверждённого PROF-001 как стартовой копии;
- owner isolation, CSRF, rate limits, bounded state/assets/metadata;
- migration, backup inventory, tests и dedicated CI gate.

Не входят AI-интервью, AI-переформулировка, template marketplace, collaborative editing, public sharing, хранение PDF binary, external object-storage provider, privacy export/delete и account retention.

## 3. Доменная модель

```text
User
  -> ResumeDraft 1..N             mutable current state
       -> ResumeVersion 0..N      immutable snapshots
       -> ResumeAsset 0..N        durable photo/logo objects
       -> ResumeExport 0..N       metadata for generated PDF
```

`ResumeDraft` не является источником подтверждённых карьерных фактов. PROF-001 остаётся canonical confirmed-facts store; черновик может быть создан из его текущего snapshot, но дальнейшие document edits не записываются обратно в PROF-001 автоматически.

## 4. Current draft и autosave

Каждый draft содержит:

```text
id, user_id
schema_version = 1
revision >= 1
title
state_json
content_hash
completion_percent
profile_version (seed provenance only)
created_at, updated_at
```

Клиент передаёт `expected_revision`. PostgreSQL row lock + equality check блокируют stale overwrite. Material change увеличивает revision; одинаковый canonical hash возвращает no-op и не меняет revision.

Autosave является mutable current state и не создаёт immutable version на каждое нажатие клавиши. Это предотвращает version spam.

## 5. Immutable versions

Версия создаётся только при:

- `checkpoint` — пользователь нажал «Сохранить версию»;
- `export` — PDF сформирован из текущего сохранённого state;
- `restore` — исторический snapshot восстановлен как новый current state и новая версия.

Одинаковый content hash при checkpoint/export повторно не создаёт duplicate snapshot. Restore всегда создаёт новую version с `restored_from_version`, сохраняя историю происхождения.

## 6. Durable assets

Фотография и эмблема не хранятся в session, localStorage или data URL внутри `state_json`. Они сохраняются как owner/draft-scoped `ResumeAsset` с MIME, размером и SHA-256; draft/version snapshot содержит только asset UUID.

Текущий staging использует PostgreSQL `LargeBinary`, потому что Render filesystem эфемерен, а отдельный object-storage provider ещё не выбран. Storage boundary изолирован в repository/service; перед multi-replica production его можно заменить S3-compatible adapter без изменения draft contract.

Для фотографии поддерживаются JPG, PNG и WebP; для найденной эмблемы дополнительно допускаются валидные GIF/ICO. Processed asset limit — 2 MiB. Сигнатура сверяется с MIME. Чужой asset ID и asset другого draft отклоняются.

## 7. PDF export contract

PDF по-прежнему генерируется в браузере из тех же paginated preview canvases. Перед export выполняется autosave flush; state-changing controls временно блокируются. Browser вычисляет SHA-256 и отправляет только metadata:

```text
version_id/version
page_count
byte_size
pdf_sha256
file_name
created_at
```

PDF binary не загружается и не хранится сервером. Immutable version фиксирует exact input snapshot, а metadata даёт audit evidence, какой version был экспортирован. Acceptance gate проверяет, что export совпадает с preview на одном locked state.

## 8. Влияние на код и сайт

Новые ключевые файлы:

```text
domain/resume_draft.py
models/resume.py
repositories/resume_drafts.py
services/resume_drafts.py
routes/resume_drafts.py
migrations/versions/20260812_0012_resume_drafts_versions.py
templates/resumes/library.html
templates/resumes/history.html
templates/resumes/version.html
tests/test_prof003_migration.py
tests/test_resume_draft_service.py
tests/test_resume_draft_routes.py
```

На сайте появляются «Мои резюме», несколько черновиков, server save state, rename/delete, checkpoint, history/read-only version, restore, durable images и export audit. `/resume-builder` теперь требует first-party login и открывает latest owner draft.

WSGI остаётся `app:app`; `app_fixed.py` не создавался. Новых Render environment variables нет.

## 9. Migration `20260812_0012`

Создаются таблицы:

```text
resume_drafts
resume_versions
resume_assets
resume_exports
```

Все owner/draft/version связи имеют foreign keys и `ON DELETE CASCADE`. Уникальны `(draft_id, version)` и `(draft_id, kind, sha256)`. Добавлены bounds/check constraints и owner/history indexes. Backup inventory включает все четыре таблицы.

## 10. Проверки и доказательства

Candidate/local evidence:

```text
split full available pytest                 252 passed, 11 skipped
focused PROF-003 migration/service/routes   15 passed, 1 skipped
Python compileall                            passed
Jinja parse (25 templates)                  passed
JavaScript syntax                            passed
SQLite 0011 -> 0012 -> 0011 -> 0012         passed
Alembic check                                passed
repository hygiene / infra manifest          passed
```

External evidence:

- GitHub CI полностью green после r1, включая dedicated PROF-003, PostgreSQL migration/integration, PROF-001/002, AUTH-001/002, encrypted backup/restore и Docker/runtime gates.
- Render `/health/ready`: PostgreSQL persistent, current/expected `20260812_0012`, migrations ok.
- Production E2E: blank/profile-seeded/multiple drafts, autosave/relogin/cross-device, checkpoint/no-op/read-only/restore, stale conflict, direct edit, iPhone photo, university logo, PDF parity, owner isolation и restart persistence.
- После restart текущий draft снова изменяется и autosave работает.

Final functional regression + Render log review: ПОДТВЕРЖДЕНО. PROF-003 COMPLETE.

## 11. Ограничения и риски

- Current browser interview remains deterministic, not AI.
- Legacy localStorage reads only for one-time migration; server becomes authoritative.
- PostgreSQL binary asset storage is suitable for current staging/one-instance volume, not an unlimited media CDN.
- No server-side PDF binary means re-download requires regeneration from version/current state.
- No automatic merge of concurrent edits; stale editor receives `409`.
- Asset retention follows draft lifetime; delete draft cascades versions/assets/export metadata.
- Privacy export/delete/retention is handled by future PRIV-001.

## 12. Rollback

Application revert may leave additive revision `0012`; previous code ignores the new tables. Controlled downgrade `0012 -> 0011` drops all resume draft/version/asset/export tables and is data-destructive after real use. It requires verified backup and explicit data decision. User/AuthSession/OAuth/Profile/Search/Sync records are not modified.

## 13. Следующее действие

```text
PROF-003 COMPLETE
-> PRIV-001 START
-> PRIV-001 candidate: export / account deletion / retention controls
-> GitHub CI -> Render 0013 -> production privacy E2E
```

## 14. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Реализованы server-side drafts, optimistic autosave, immutable versions, history/restore, durable assets, export metadata, migration `0012`, UI и tests; требуется внешний gate. |
| 1.1 | 13.08.2026 | Green CI/Render `0012`, production E2E и restart persistence записаны; hotfix r1-r4 подтверждены. Остаётся final regression/log review. |
| 1.2 | 13.08.2026 | Final regression `/profile`/PROF-002/`/dashboard`/AUTH/OAuth/`/vacancies`, readiness `0012` and Render log privacy/error review confirmed; PROF-003 COMPLETE, PRIV-001 next. |
