# AI Career Agent — дорожная карта

| Поле | Значение |
|---|---|
| Версия | 1.4.9 |
| Дата | 2026-08-09 |
| Источник | `docs/PLAN_CURRENT.md` |
| Текущий gate | SEARCH-003 GitHub/Render verification |

## 1. Функциональная очередь без аренды VPS

```text
SEARCH-003 verification
→ SEARCH-004
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
| SEARCH-001 | ВЫПОЛНЕНО | Typed contract и canonical filters |
| SEARCH-002 | ВЫПОЛНЕНО | Conservative reversible cross-source dedup |
| SEARCH-003 | НУЖНА ПРОВЕРКА | CI + Render revision 0007 + cross-page smoke |
| SEARCH-004/005 | ЗАПЛАНИРОВАНО | Canonical route/admin source status |
| INFRA-001 | ОТЛОЖЕНО | Real VPS перед beta |

## 4. SEARCH-003 gate

```text
persistent bounded snapshot
+ per-provider cursor state
+ canonical filter/dedup before ordinal
+ deterministic global sort
+ committed page prefix
+ honest totals
+ TTL cleanup
```

Пакет закрывается только после зелёного CI и production проверки page 0 → page 1 → page 0 с одним snapshot ID.

## 5. Ограничения

- Exact total не вычисляется массовым synchronous scan upstream.
- `/vacancies/internal` остаётся до SEARCH-004.
- Dedup thresholds SEARCH-002 не меняются.
- Real VPS остаётся предрелизным gate.
