# AI Career Agent — реализация PROF-002

| Поле | Значение |
|---|---|
| Документ | PROF002_IMPLEMENTATION |
| Пакет | PROF-002 |
| Версия | 1.0 |
| Дата | 12 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Рабочая основа | GitHub `main` commit `f5e513f0f992b20305fbef36851ef97576013c86`, полностью совпадающий с загруженным ZIP |
| Production revision до deploy | `20260811_0010` |
| Candidate revision | `20260812_0011` |

## 1. Контрольный статус

PROF-002 реализован как candidate. Пакет добавляет безопасный путь `PDF-резюме -> извлечение предложений -> редактируемая проверка -> явное подтверждение -> новая immutable версия PROF-001`. Статус остаётся `НУЖНА ПРОВЕРКА` до зелёного Pull Request CI, Render migration `0011` и production E2E.

## 2. Цель и границы

Цель — убрать повторный ручной ввод существующей карьерной истории, не превращая автоматическое извлечение в подтверждённые факты.

В scope:

- upload текстового PDF только authenticated first-party User;
- существующие лимиты размера, страниц и текста;
- детерминированное извлечение контактов, позиционирования, локации, навыков, опыта, образования, языков и достижений;
- confidence/evidence/warnings для review;
- merge с текущим PROF-001 без тихой замены подтверждённых scalar facts;
- полная редактируемая форма перед сохранением;
- явная кнопка подтверждения;
- owner-bound, time-limited signed review metadata;
- provenance в immutable `CareerProfileVersion`;
- owner/version conflict protection;
- отдельный CI gate и positive/negative tests.

Не входят OCR сканов, DOC/DOCX, provider resume import, LLM/AI parsing, background jobs, persisted drafts, autosave, historical restore и автоматическое подтверждение данных.

## 3. Пользовательский поток

```text
verified first-party session
-> /profile/import
-> upload PDF
-> safe text extraction
-> ephemeral proposal
-> editable review form
-> user corrects/removes/adds facts
-> explicit confirm POST
-> PROF-001 validation + optimistic version check
-> immutable confirmed version with resume_import provenance
```

Upload и extracted text не сохраняются. До confirm POST в `career_profiles` и `career_profile_versions` ничего не записывается.

## 4. Extraction и merge

`services/resume_import.py` использует bounded deterministic rules поверх `pypdf` text extraction. Результат — `ResumeImportProposal`, а не profile record.

Основные правила:

- scalar suggestion заполняет пустое поле;
- если scalar уже подтверждён и отличается, текущее значение сохраняется, а review показывает conflict;
- списки и строки объединяются case-insensitive по стабильному ключу;
- неизвестные значения не угадываются;
- недостаточно распознанные секции получают warning;
- если нет ни одного структурированного signal, import отклоняется.

## 5. Confirmation boundary

Подтверждением является только отправка обычной формы PROF-001 через `/profile/import/confirm`.

Signed token хранит только bounded metadata:

- schema/extractor version;
- page/character counts;
- detected section codes;
- confidence codes;
- static warnings;
- HMAC owner fingerprint;
- base profile version;
- issued timestamp.

Token не содержит filename, PDF bytes, extracted text, contacts или proposed profile payload. Proposal остаётся в browser form. Owner может свободно исправить форму; сохранится только фактически отправленный и валидированный payload.

## 6. Persistence и migration

Migration `20260812_0011_profile_import_provenance` добавляет в `career_profile_versions`:

```text
source_kind      VARCHAR(32) NOT NULL DEFAULT 'manual'
provenance_json  TEXT NOT NULL DEFAULT '{}'
CHECK source_kind IN ('manual', 'resume_import')
```

Существующие версии получают `manual` и пустой provenance. Current profile schema version остаётся `1`: migration меняет audit metadata версии, а не canonical facts contract.

`resume_import` provenance содержит только агрегаты extraction/review; filename и факты профиля туда не входят.

## 7. Влияние на код и сайт

Новые ключевые файлы:

```text
domain/resume_import.py
services/resume_import.py
migrations/versions/20260812_0011_profile_import_provenance.py
templates/profile/import_upload.html
tests/test_prof002_migration.py
tests/test_resume_import_service.py
tests/test_resume_import_routes.py
```

Изменены `app.py`, profile service/model/repository/routes/templates/styles, PostgreSQL integration test, CI и документация.

На сайте появились:

- `Импортировать резюме` в профиле и кабинете;
- upload page;
- review screen на базе существующего editor;
- confidence/warnings/conflicts/evidence;
- source label в истории и historical version.

WSGI остаётся `app:app`; `app_fixed.py` не создавался. Новых environment variables нет.

## 8. Проверки и доказательства

Локально на candidate:

```text
full available pytest: 246 passed, 10 skipped
focused migration/service/parser: 15 passed
profile/template/architecture subset: 23 passed
compileall: passed
Jinja parse: 22 templates passed
SQLite clean upgrade to 0011: passed
SQLite 0011 -> 0010 -> 0011: passed
Alembic check: no new upgrade operations
```

Flask route и PostgreSQL tests локально skipped только из-за отсутствующих runtime dependencies/service; они включены в GitHub Actions.

## 9. Ограничения и риски

- Детерминированный parser не равен AI и может неправильно структурировать нестандартное резюме.
- Image-only PDF возвращает безопасную ошибку; OCR исключён.
- PDF с сложной многоколоночной версткой может давать низкую уверенность.
- Review metadata живёт 30 минут и не является persisted draft.
- Re-upload требуется после stale profile conflict или истечения token.
- Импорт не определяет salary/work preferences, если их нет в безопасно распознаваемой форме.
- Raw resume text нельзя логировать, хранить в token/provenance или canonical docs.

## 10. Rollback

1. Остановить новые import actions и вернуть предыдущий application commit.
2. Revision `0011` можно оставить: предыдущий код игнорирует новые nullable-by-default audit columns.
3. Controlled downgrade `0011 -> 0010` удаляет только `source_kind`, `provenance_json` и check constraint; canonical profile/version snapshots не удаляются.
4. Не удалять users, auth sessions, OAuth connections, profile snapshots, search/sync data.
5. Если обнаружена утечка resume text, действовать по SEC/OPS incident procedure и отозвать затронутые sessions.

## 11. Следующее действие

```text
PROF-002 CANDIDATE
-> Pull Request CI
-> Render 20260812_0011
-> real PDF review/confirm E2E
-> owner/stale/no-persistence/restart/regression checks
-> PROF-002 COMPLETE
-> PROF-003 START
```

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 12.08.2026 | Реализованы ephemeral PDF proposal, editable review, explicit confirmation, provenance migration `0011`, UI и tests; требуется внешний gate. |
