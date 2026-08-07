AI Career Agent — SYNC-001 candidate v1.4.1

1. Создать ветку от актуального main: sync-001-external-worker
2. Загрузить полный проект с заменой файлов.
3. Убедиться, что dotfiles и .github/workflows/ci.yml присутствуют.
4. Commit: sync: move Trudvsem updates out of Gunicorn
5. Merge только после полностью зелёного GitHub Actions.
6. Для существующего Render service вручную установить Start Command:
   python scripts/manage_db.py upgrade && python scripts/start_runtime.py
7. После deploy выполнить docs/SYNC001_VERIFICATION_STATUS.md.

Не добавлять .env, secrets, databases, dumps, backups, virtualenv, caches или bytecode.
