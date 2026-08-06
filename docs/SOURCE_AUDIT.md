# AI Career Agent — аудит источников

**Версия аудита:** 1.3.2  
**Дата:** 06 августа 2026  
**Пакет:** SEC-001 rate-limit fix поверх OPS-001

## Результат

### Актуальный код

Рабочей основой признан архив `ai-career-agent-site-main-16-ops-001-observability-backup-v1.3.1.zip`, потому что именно он содержит уже реализованный OPS-001 (`observability.py`, `operations/backup.py`, operational tests и runbooks). Исправление SEC-001 внесено непосредственно поверх этой версии без отката observability, backup/restore или документации OPS-001.

### Актуальные документы до исправления

- `AI_Career_Agent_PLAN_CURRENT_v1.3.1_2026-08-05` — план OPS-001 candidate;
- `AI_Career_Agent_Паспорт_проекта_v2.9_2026-08-05` — связанный паспорт;
- они фиксируют SEC-001 и OPS-001 как ожидающие проверки и сохраняют последовательность VPS/Alice AI/Reed/domain/migration.

### Проверка состава ZIP

Архив содержит SEC-001, OPS-001, PostgreSQL/Alembic revision `20260804_0002`, актуальный CI, root `.gitignore`, operational runbooks и не содержит временного `README_FIRST.txt`. В исправлении изменены только security/rate-limit wiring, regression tests, CI security step и связанная документация.

## Новые канонические источники

- PLAN_CURRENT `1.3.2`;
- паспорт `2.10`;
- проектный ZIP `ai-career-agent-site-main-17-sec-001-rate-limit-fix-ops-001-v1.3.2.zip`.

Старые документы ниже PLAN_CURRENT 1.3.2 и паспорта 2.10 после загрузки новых источников не должны считаться действующими.


## Проверка 06 августа 2026

Production smoke подтвердил CSP/HSTS, secure cookie, CSRF 400, PostgreSQL revision, страницы, поиск, PDF, закрытые diagnostics и безопасные application logs. Единственное расхождение: 25 последовательных обращений к декорированному лимитом маршруту не дали `429`, потому что `get_remote_address` видел меняющиеся Render proxy addresses. Исправление внесено в актуальный OPS-001 ZIP без удаления observability/backup кода.
