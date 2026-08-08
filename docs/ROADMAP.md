# AI Career Agent — дорожная карта

| Поле | Значение |
|---|---|
| Версия | 1.4.3 |
| Дата | 2026-08-07 |
| Источник | `docs/PLAN_CURRENT.md` |
| Текущий gate | SYNC-002 GitHub/Render verification |

## 1. Функциональная очередь без аренды VPS

```text
SYNC-002 verification
→ SEARCH-001 → SEARCH-002 → SEARCH-003 → SEARCH-004
→ AUTH-001 → AUTH-002
→ PROF-001 → PROF-002 → PROF-003 → PRIV-001
→ SEARCH-005
→ AI-BENCH-001 → AI-PROVIDER-001 → LEGAL-001
→ AI-001 → AI-002 → AI-003 → AI-004 → AI-005 → AI-006
→ JOB-001 → JOB-002 → JOB-003/JOB-004
```

## 2. Предрелизный инфраструктурный блок

```text
INFRA-001
→ REED-COMPAT-001
→ HOST-001
→ OPS-002 + production backup/restore
→ DOMAIN-001
→ MIG-001
→ REL-001
```

## 3. Пакеты

| ID | Статус | Следующее действие |
|---|---|---|
| FND-001/FND-002 | ВЫПОЛНЕНО | Базовая платформа |
| DATA-001/DATA-002 | ВЫПОЛНЕНО | PostgreSQL и domain/repository layer |
| SEC-001 | ВЫПОЛНЕНО | Production security baseline |
| OPS-001 | ВЫПОЛНЕНО | Observability и backup tooling |
| INFRA-PREP-001 | ВЫПОЛНЕНО | Container portability |
| DOC-001 | В РАБОТЕ | Синхронизация с каждым package |
| SYNC-001 | ВЫПОЛНЕНО | External worker production verified |
| SYNC-002 | НУЖНА ПРОВЕРКА | CI, migration 0004, checkpoint/cleanup Render smoke |
| SEARCH-001 | ЗАПЛАНИРОВАНО | Начать после подтверждения SYNC-002 |
| INFRA-001 | ОТЛОЖЕНО | Реальный VPS перед beta |
