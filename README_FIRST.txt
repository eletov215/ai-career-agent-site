AI Career Agent — SEARCH-002 candidate v1.4.7

1. Создать ветку от актуального main: search-002-cross-source-dedup
2. Загрузить полный проект с заменой файлов.
3. Убедиться, что .github, .gitignore, .dockerignore и migration 20260809_0006 присутствуют.
4. Commit: search: add conservative cross-source deduplication
5. Merge только после полностью зелёного GitHub Actions.
6. Render Start Command не менять:
   python scripts/manage_db.py upgrade && python scripts/start_runtime.py
7. После deploy проверить /health/ready revision 20260809_0006 и выполнить docs/SEARCH002_RUNBOOK.md.

Не добавлять .env, secrets, databases, dumps, backups, virtualenv, caches или bytecode.
