# AI Career Agent — export/privacy data contract reference PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_EXPORT_REFERENCE |
| Пакет | PRIV-001 |
| Версия | 1.2 |
| Дата | 19 августа 2026 |
| Статус | ВЫПОЛНЕНО |

## 1. Purpose

Reference фиксирует технический inventory/export/delete/retention contract текущих first-party data. Это не legal privacy policy.

## 2. Export inventory

| Категория | Export | Delete with account | Retention cleanup |
|---|---|---|---|
| User account metadata | да | да | stale pending only |
| Password hash | НЕТ | да | with User |
| Auth session/token metadata | да, без hashes/secrets | да | expired/revoked/consumed |
| Auth hashes/secrets | НЕТ | да | bounded auth cleanup |
| HH/SJ identity/profile metadata | sanitised | да | active User не age-out |
| HH/SJ access/refresh/browser secrets | НЕТ | да local | active User не age-out |
| CareerProfile current/versions | да | да | no inactivity cleanup |
| ResumeDraft current/versions | да | да | no inactivity cleanup |
| Referenced resume image bytes | да | да | orphan-only 7d |
| Resume PDF export metadata | да | да | no inactivity cleanup |
| Resume PDF binary | отсутствует server-side | n/a | n/a |
| Identifier-free privacy audit | не owner export | aged by policy | 180d default |

## 3. Export structure and safety

`manifest.json` declares schema/time/categories/exclusions; `data.json` stores JSON-safe owner data. Referenced owned assets are separate files. Missing asset references mean `assets/` may be absent. ZIP entry path components are sanitized; archive/raw size are bounded; PostgreSQL snapshot is consistent; response is no-store.

## 4. Secret exclusion rule

Never export password/auth/session/token hashes, OAuth access/refresh/browser secrets, code verifier/device/user codes/SAML/token-like credentials or server environment secrets. Provider profile URLs/strings are sanitized.

## 5. Account deletion graph

```text
User
-> AuthSession / AuthToken
-> OAuthConnection
-> CareerProfile -> CareerProfileVersion
-> ResumeDraft -> ResumeVersion / ResumeAsset / ResumeExport
```

Legacy HH/SJ local mirrors are explicitly cleaned. Shared Vacancy/Search/Sync rows are not one User's owner subtree.

## 6. Retention categories

```text
pending unverified User      30d default
expired/revoked auth data    30d default
orphan ResumeAsset             7d default
identifier-free audit        180d default
active owner content          until explicit deletion
```

No rule guesses inactivity for active verified User. Orphan asset delete requires no current/history reference after recheck.

## 7. Provider and backup distinction

Local deletion != remote provider grant revocation. Existing backup copies are not rewritten by account deletion. Provider revoke and final backup/legal retention are separate future gates.

## 8. Production evidence

Export with correct password worked. Account without image refs returned only manifest/data; forbidden credential fields absent. Account with university logo exported owned asset. Destructive throwaway deletion and restart/regression completed without affecting independent account.

## 9. Future compatibility

AI/JOB/BILL data must be explicitly added before future packages can claim export/delete coverage. Incompatible export shape requires explicit schema versioning.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Initial inventory and exclusions. |
| 1.1 | 19.08.2026 | Hardened snapshot/bounds/sanitizer/orphan asset rules. |
| 1.2 | 19.08.2026 | Production export/assets/deletion evidence confirmed; COMPLETE. |
