AI Career Agent — SEARCH-004 candidate v1.4.11

1. Создать ветку от актуального main:
   search-004-canonical-vacancies

2. Скопировать содержимое полного архива в локальный GitHub Desktop
   repository с заменой файлов. Папку .git не удалять и не заменять.

3. Проверить, что сохранены служебные файлы и новые элементы:
   .github/
   .gitignore
   .dockerignore
   services/source_status.py
   tests/test_source_status.py
   docs/SEARCH004_IMPLEMENTATION.md
   docs/SEARCH004_VERIFICATION_STATUS.md
   docs/SEARCH004_RUNBOOK.md
   docs/SEARCH004_SOURCE_STATE_REFERENCE.md

4. Commit:
   search: make vacancies route canonical and expose safe source states

5. Merge выполнять только после полностью зелёного GitHub Actions,
   включая шаг:
   Verify SEARCH-004 canonical route and source-state controls

6. Render Start Command не менять:
   python scripts/manage_db.py upgrade && python scripts/start_runtime.py

7. После deploy проверить:
   /health/ready
   current_revision = expected_revision = 20260809_0007

8. Выполнить production smoke по docs/SEARCH004_RUNBOOK.md:
   /vacancies -> 200;
   /vacancies/internal?<query> -> 308 на /vacancies;
   repeated source, snapshot и page сохранены;
   Trudvsem отображается как cached/degraded;
   недоступный provider не вызывается и не раскрывает технические детали;
   pagination и generated links используют /vacancies.

Не добавлять .env, secrets, databases, dumps, backups, virtualenv,
caches или bytecode.

SEARCH-004 остаётся в статусе НУЖНА ПРОВЕРКА до зелёного CI и Render smoke.
После закрытия следующий обязательный пакет по PLAN_CURRENT — AUTH-001.
