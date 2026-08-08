# AI Career Agent — дорожная карта

| Поле | Значение |
|---|---|
| Версия | 1.4.5 |
| Дата | 2026-08-08 |
| Источник | `docs/PLAN_CURRENT.md` |
| Текущий gate | SEARCH-001 GitHub/Render verification |

## 1. Функциональная очередь без аренды VPS

```text
SEARCH-001 verification
→ SEARCH-002 → SEARCH-003 → SEARCH-004
→ AUTH-001 → AUTH-002
→ PROF-001 → PROF-002 → PROF-003 → PRIV-001
→ SEARCH-005
→ AI-BENCH-001 → AI-PROVIDER-001 → LEGAL-001
→ AI-001 → AI-002 → AI-003 → AI-004 → AI-005 → AI-006
→ JOB-001 → JOB-002 → JOB-003/JOB-004
```

## 2. Предрелизный инфраструктурный блок

```text
INFRA-001 → REED-COMPAT-001 → HOST-001
→ OPS-002 + production backup/restore
→ DOMAIN-001 → MIG-001 → REL-001
```

## 3. Пакеты

| ID | Статус | Следующее действие |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО | Базовая платформа |
| DOC-001 | В РАБОТЕ | Единый template v1.1 с каждым package |
| SYNC-001 / SYNC-002 | ВЫПОЛНЕНО | External worker и incremental lifecycle |
| SEARCH-001 | НУЖНА ПРОВЕРКА | GitHub CI, migration 0005, Render search smoke |
| SEARCH-002 | ЗАПЛАНИРОВАНО | Cross-source dedup после SEARCH-001 |
| SEARCH-003/004/005 | ЗАПЛАНИРОВАНО | Pagination/route/admin source status |
| INFRA-001 | ОТЛОЖЕНО | Real VPS перед beta |
