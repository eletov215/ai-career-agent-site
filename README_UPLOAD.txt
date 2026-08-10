SEARCH-004 candidate v1.4.11

Upload the complete project into a branch created from current main:
  search-004-canonical-vacancies

Recommended commit:
  search: make vacancies route canonical and expose safe source states

Required files/directories that must be preserved:
  .github/
  .gitignore
  .dockerignore
  services/source_status.py
  tests/test_source_status.py
  docs/SEARCH004_*.md

Expected GitHub Actions step:
  Verify SEARCH-004 canonical route and source-state controls

No new migration. Expected revision after deploy:
  20260809_0007

Do not upload .env, secrets, databases, dumps, backups, virtualenv,
caches or bytecode.
