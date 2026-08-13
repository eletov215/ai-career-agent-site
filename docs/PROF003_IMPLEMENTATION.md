# AI Career Agent — реализация PROF-003

| Поле | Значение |
|---|---|
| Документ | PROF003_IMPLEMENTATION |
| Пакет | PROF-003 |
| Версия | 1.0 |
| Дата | 13 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Рабочая основа | GitHub `main` после PROF-002 COMPLETE + upload-limit hotfix r2 |
| Production baseline | `20260812_0011` |
| Candidate schema | `20260812_0012` |

## 1. Контрольный статус

PROF-003 реализован как candidate. Он заменяет browser-only `localStorage` в конструкторе резюме owner-scoped серверными черновиками, optimistic autosave, immutable версиями, историей/восстановлением, durable image assets и audit metadata PDF-экспорта. Статус остаётся **НУЖНА ПРОВЕРКА** до green Pull Request CI, Render revision `0012` и production E2E.

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

Доступные локальные проверки candidate:

```text
split full available pytest                 252 passed, 11 skipped
focused PROF-003 migration/service/routes     15 passed, 1 skipped
Python compileall                            passed
Jinja parse (25 templates)                  passed
JavaScript syntax (node --check)            passed
SQLite clean upgrade to 0012                passed
SQLite 0011 -> 0012 -> 0011 -> 0012         passed
Alembic check                               passed
architecture/template checks                passed
repository hygiene / infra manifest          passed
```

Flask route tests и PostgreSQL integration должны быть окончательно подтверждены GitHub Actions, где устанавливаются runtime dependencies и поднимается PostgreSQL 17.

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
PROF-003 CANDIDATE
-> separate branch / Pull Request
-> green dedicated/full CI
-> Render migration 20260812_0012
-> owner/autosave/history/restore/assets/export/restart/mobile E2E
-> PROF-003 COMPLETE
-> PRIV-001 START
```

## 14. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Реализованы server-side drafts, optimistic autosave, immutable versions, history/restore, durable assets, export metadata, migration `0012`, UI и tests; требуется внешний gate. |
