AI Career Agent — SEARCH-003 candidate v1.4.9

1. Создать ветку от актуального main:
   search-003-stable-pagination
2. Загрузить полный проект с заменой файлов через GitHub Desktop.
3. Убедиться, что сохранены служебные файлы и каталоги:
   .github/
   .gitignore
   .dockerignore
   migrations/versions/20260809_0007_stable_search_snapshots.py
4. Commit:
   search: add persistent stable pagination and honest totals
5. Merge выполнять только после полностью зелёного GitHub Actions, включая шаг:
   Verify SEARCH-003 stable pagination and totals controls
6. Render Start Command не менять:
   python scripts/manage_db.py upgrade && python scripts/start_runtime.py
7. После deploy проверить:
   /health/ready
   current_revision = expected_revision = 20260809_0007
8. Выполнить production smoke по docs/SEARCH003_RUNBOOK.md:
   page 0 -> page 1 -> page 0 с одним snapshot ID;
   карточки между соседними страницами не повторяются;
   первая страница после возврата не меняется;
   /health/search-pagination?snapshot=<ID> показывает secret-free snapshot state.

Не добавлять .env, secrets, databases, dumps, backups, virtualenv, caches или bytecode.
SEARCH-003 остаётся в статусе НУЖНА ПРОВЕРКА до зелёного CI и Render smoke.
