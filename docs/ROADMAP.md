# AI Career Agent — дорожная карта

| Поле | Значение |
|---|---|
| Версия | 1.4.18 |
| Дата | 2026-08-11 |
| Источник | `docs/PLAN_CURRENT.md` |
| Текущий gate | AUTH-002 GitHub/Render/real HH+SuperJob ownership E2E |

## 1. Функциональная очередь без аренды VPS

```text
AUTH-002 verification
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
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО | Search/data foundation |
| AUTH-001 | ВЫПОЛНЕНО | First-party email/password foundation |
| AUTH-002 | НУЖНА ПРОВЕРКА | CI, Render 0009, real HH/SJ ownership E2E |
| PROF/PRIV/SEARCH-005 | ЗАПЛАНИРОВАНО | Account-owned product data/admin |
| DOC-001 | В РАБОТЕ | DOC-STD-001 with every package |
| INFRA-001 | ОТЛОЖЕНО | Real VPS before beta |

## 4. AUTH-002 gate

```text
owner-bound OAuthConnection
state bound to User/AuthSession
no email auto-link
unique external identity + one provider slot per User
encrypted owner-scoped refresh/disconnect
GitHub/PostgreSQL green
Render 0009
real HH and SuperJob bind/reconnect/disconnect
cross-user conflict negative smoke
```

## 5. Ограничения

- External APIs are mocked in CI.
- Remote token revoke is excluded from candidate; local credentials are deleted.
- Phone/social identities, admin merge and profile import are separate packages.
- Gmail API remains staging-only; domain sender/SPF/DKIM/DMARC is a pre-release gate.
