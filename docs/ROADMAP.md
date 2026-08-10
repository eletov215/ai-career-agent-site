# AI Career Agent — дорожная карта

| Поле | Значение |
|---|---|
| Версия | 1.4.11 |
| Дата | 2026-08-10 |
| Источник | `docs/PLAN_CURRENT.md` |
| Текущий gate | SEARCH-004 GitHub/Render verification |

## 1. Функциональная очередь без аренды VPS

```text
SEARCH-004 verification
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
| DOC-001 | В РАБОТЕ | Единый DOC-STD-001 с каждым package |
| SYNC-001 / SYNC-002 | ВЫПОЛНЕНО | External worker и incremental lifecycle |
| SEARCH-001 / SEARCH-002 / SEARCH-003 | ВЫПОЛНЕНО | Contract, dedup, stable pagination |
| SEARCH-004 | НУЖНА ПРОВЕРКА | Canonical route + safe public source states |
| SEARCH-005 | ЗАПЛАНИРОВАНО | Protected admin source center |
| INFRA-001 | ОТЛОЖЕНО | Real VPS перед beta |

## 4. SEARCH-004 gate

```text
/vacancies 200
+ /vacancies/internal permanent method-preserving redirect
+ query/snapshot/page preservation
+ canonical forms/pagination/navigation
+ safe available/cached/degraded/auth-required/unavailable states
+ Trudvsem cache explicitly labeled
+ no credential/error leakage
```

Пакет закрывается только после зелёного CI и Render route/search/source-state smoke.

## 5. Ограничения

- Migration отсутствует; revision остаётся `20260809_0007`.
- Redirect использует permanent method-preserving `308`; no-store защищает verification window от stale cache.
- Admin telemetry относится к SEARCH-005.
- SEARCH-003 snapshot algorithm и SEARCH-002 dedup thresholds не меняются.
