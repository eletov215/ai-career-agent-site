# AI Career Agent — privacy data contract reference PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_PRIVACY_REFERENCE |
| Пакет | PRIV-001 |
| Версия | 1.1 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Purpose

Reference фиксирует технический inventory и lifecycle текущих first-party personal data. Это не юридическая privacy policy; финальные legal bases/wording/retention утверждаются `LEGAL-001`.

## 2. Export inventory

| Категория | Export | Delete with account | Retention cleanup |
|---|---|---|---|
| User account metadata | да | да | stale pending only |
| Password hash | НЕТ | да | with User |
| Auth session/token metadata | да, без hashes | да | expired/revoked/consumed |
| Auth token/session hashes | НЕТ | да | expired/revoked/consumed |
| HH/SJ external identity/profile metadata | да | да | нет для active User |
| HH/SJ access/refresh token | НЕТ | да local | нет для active User |
| CareerProfile current/version snapshots | да | да | нет для active User |
| ResumeDraft current/version snapshots | да | да | нет для active User |
| Resume image asset bytes | да | да | нет для active User |
| Resume PDF export metadata | да | да | нет для active User |
| Resume PDF binary | отсутствует server-side | n/a | n/a |
| Privacy audit | не owner-linked; не экспортируется как personal record | aged by policy | 180d default |

## 3. Export structure

Manifest сообщает schema/version/time/categories/secret exclusions. `data.json` хранит JSON-safe values and timestamps. Assets сохраняются отдельными binary files; state JSON продолжает использовать UUID references.

## 4. Secret exclusion rule

Authentication credentials не являются portability payload. Никогда не экспортируются:

```text
password_hash
auth session token/hash
auth verification/reset token hash
OAuth access_token
OAuth refresh_token
OAuth state/browser secret
server environment secrets
```

## 5. Account deletion graph

```text
User
-> AuthSession / AuthToken
-> OAuthConnection
-> CareerProfile -> CareerProfileVersion
-> ResumeDraft -> ResumeVersion / ResumeAsset / ResumeExport
```

Unified owner rows удаляются cascade. Legacy HH/SuperJob credential mirrors удаляются explicit repository cleanup до User delete. Shared Vacancy/Search/Sync data не является owner subtree и не удаляется вместе с одним User.

## 6. Retention categories

```text
pending unverified User      30d default
expired/revoked auth data    30d default
identifier-free audit       180d default
active owner content         until explicit deletion
```

No cleanup rule guesses inactivity for an active verified User.

## 7. OAuth distinction

Local deletion != remote grant revocation. After account deletion AI Career Agent no longer retains local HH/SuperJob token material, but provider-side authorization state may require future provider revoke integration or user action on provider account.

## 8. Future compatibility

New AI usage/job-tracker/billing data must be explicitly added to this inventory before those packages can claim export/delete coverage. `LEGAL-001` may revise retention values; schema/config should remain versioned.

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Defined export/delete/retention inventory and secret exclusions for current AUTH/PROF data model. |

## Hardened candidate v1.4.28

Повторный privacy/security аудит перед внешней проверкой усилил candidate: экспорт требует повторного текущего пароля и формируется как согласованный PostgreSQL snapshot; добавлены raw/archive size bounds, SpooledTemporaryFile, safe ZIP entry paths, OAuth profile sanitization и fail-closed owner/draft asset integrity. Account deletion повторно сверяет password hash под User row lock и использует единый lock order для Auth/OAuth rows. Retention cleanup получил bounded batches, orphan ResumeAsset cleanup (7d, только без current/history references), cross-process worker lock/heartbeat и индекс `idx_resume_assets_created`. Backup copies не переписываются account deletion; remote provider-side OAuth revoke не заявляется. Candidate schema остаётся `20260813_0013`; production до merge остаётся `20260812_0012`.
