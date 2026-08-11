# AI Career Agent — дорожная карта

| Поле | Значение |
|---|---|
| Версия | 1.4.16 |
| Дата | 2026-08-11 |
| Источник | `docs/PLAN_CURRENT.md` |
| Текущий gate | AUTH-001 Gmail API HTTPS delivery + Render E2E verification |

## 1. Функциональная очередь без аренды VPS

```text
AUTH-001 verification
→ AUTH-002
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
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО | Search/data foundation |
| AUTH-001 | НУЖНА ПРОВЕРКА | CI, migration 0008, SMTP, account E2E |
| AUTH-002 | ЗАПЛАНИРОВАНО | Bind HH/SJ OAuth to first-party User |
| PROF/PRIV/SEARCH-005 | ЗАПЛАНИРОВАНО | Account-owned product data/admin |
| INFRA-001 | ОТЛОЖЕНО | Real VPS перед beta |

## 4. AUTH-001 gate

```text
versioned scrypt + no plaintext
hashed TTL/single-use tokens
revocable PostgreSQL sessions
CSRF/rate limits/enumeration-safe responses
GitHub/PostgreSQL green
Render 0008 + SMTP configured; Safari CSRF pass confirmed; Mail.ru delivery pending
registration/verification/login/logout/revoke/reset E2E
```

## 5. Ограничения

- OAuth binding остаётся AUTH-002.
- Production email provider не поставляется кодом; operator config обязателен.
- Revision 0008 additive; downgrade после real accounts запрещён без backup/decision.
- MFA/account deletion/export/admin roles не входят.

## 5. Pre-release email infrastructure gate

Gmail API используется только для staging на Render Free. До beta/commercial release обязателен переход на sender собственного домена (целевой пример `noreply@ai-career-agent.ru`) с production-grade transactional delivery и SPF/DKIM/DMARC.
