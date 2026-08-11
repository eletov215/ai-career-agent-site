# AI Career Agent — статус проверки AUTH-001

| Поле | Значение |
|---|---|
| Документ | AUTH001_VERIFICATION_STATUS |
| Пакет | AUTH-001 |
| Версия | 1.3 |
| Дата | 11 августа 2026 |
| Статус | ВЫПОЛНЕНО |
| Production revision | `20260810_0008` |

## 1. Контрольный статус

AUTH-001 закрыт как ВЫПОЛНЕНО. GitHub Actions полностью зелёный, включая dedicated `Verify AUTH-001 first-party account controls` и прежние PostgreSQL/SEC/OPS/SYNC/SEARCH/Docker gates. Render `/health/ready` подтверждает Gmail API staging backend, persistent PostgreSQL и актуальную migration. Реальная email delivery и полный account E2E подтверждены в production staging.

## 2. Матрица критериев

| Критерий | Статус | Доказательство |
|---|---|---|
| Existing `users` как identity root | ПРОЙДЕНО | Production account создан и подтверждён |
| Email normalization + unique identity | ПРОЙДЕНО | Registration flow завершён без duplicate identity regression |
| Scrypt salted/versioned hash; no plaintext | ПРОЙДЕНО | Green AUTH-001 tests + password reset/login E2E |
| Verification TTL + one-way + single-use | ПРОЙДЕНО | Used verification link неактивен; superseded previous link неактивен |
| Atomic verification/session state | ПРОЙДЕНО | Verification активирует account; session count отражается на dashboard |
| Session rotation + server-side logout/revoke | ПРОЙДЕНО | 2 independent sessions; individual revoke and revoke-others invalidate other browser context |
| Enumeration-safe register/reset/login copy | ПРОЙДЕНО | Covered by dedicated tests; public recovery copy remains neutral |
| CSRF/rate-limit/no-store/strict-origin | ПРОЙДЕНО | Safari production register/verify/auth actions complete after strict-origin hotfix |
| Migration `0008` + PostgreSQL CI | ПРОЙДЕНО | GitHub green; Render current=expected=`20260810_0008` |
| Dedicated AUTH-001 CI gate | ПРОЙДЕНО | GitHub Actions green |
| Gmail API HTTPS transport | ПРОЙДЕНО | `/health/ready`: `gmail_api`, configured=true; real verification email received |
| Register/verify/login/logout/revoke E2E | ПРОЙДЕНО | Production staging user flow confirmed |
| Forgot/reset + old sessions invalid | ПРОЙДЕНО | Password changed; old password rejected; pre-reset session invalidated; new password accepted |
| Reset token single-use | ПРОЙДЕНО | Reuse of consumed reset link rejected |

## 3. Проверки и доказательства

### 3.1 Local/candidate evidence

```text
Full available pytest: 229 passed, 7 skipped
Focused AUTH-001 gate: 95 passed, 2 skipped
Focused Gmail/config/infra tests: 77 passed
Compileall: passed
Document structure: passed
Infra manifest: passed
Repository hygiene: passed
Alembic head/check: 20260810_0008 / no new operations
```

External Google calls are mocked in CI. No OAuth secret is required by tests.

### 3.2 GitHub evidence

GitHub Actions after Gmail API integration completed green, including:

```text
Verify AUTH-001 first-party account controls
PostgreSQL migration/integration gates
SEC / OPS / SYNC / SEARCH regression gates
backup/restore and Docker/container gates
full pytest run
```

### 3.3 Render readiness evidence

Production staging `/health/ready` confirmed:

```text
status = ok
auth.email_backend = gmail_api
auth.email_delivery_configured = true
database.backend = postgresql
database.configured = true
database.ok = true
database.persistent = true
database.revision = 20260810_0008
migrations.current_revision = 20260810_0008
migrations.expected_revision = 20260810_0008
migrations.ok = true
oauth_configured = true
```

### 3.4 Real AUTH E2E evidence

Production staging test confirmed in sequence:

1. Registration with a normal external email account.
2. Verification email delivered through Gmail API HTTPS.
3. Verification link requires explicit confirmation action.
4. Consumed verification link becomes inactive.
5. Previous superseded verification link is inactive.
6. Email/password login succeeds after verification.
7. Two independent server-side sessions exist using normal/private Safari contexts.
8. Individual revoke removes the selected session and that browser context is redirected to login.
9. `Завершить другие` revokes all other sessions while current session remains valid.
10. Logout revokes current session; direct `/dashboard` access redirects to login/registration.
11. Forgot-password email delivery succeeds through Gmail API.
12. Password reset succeeds.
13. Old password is rejected.
14. Session created before reset is invalidated.
15. New password login succeeds.
16. Consumed reset link cannot be reused.

## 4. Влияние на код и сайт

No final verification code change is required. The completed implementation remains the v1.4.16 Gmail API-capable AUTH-001 code on schema `20260810_0008`. This release synchronizes status/evidence and hands development to AUTH-002.

## 5. Ограничения и риски

- Gmail API is a temporary staging transport for Render Free, not the commercial sender.
- The test Gmail message may be classified as spam; this does not block AUTH-001 functional completion but is unacceptable for commercial delivery.
- Google Auth Platform Testing may expire/revoke the staging refresh token and require re-authorization.
- Before beta/commercial release, switch to a project-owned domain sender such as `noreply@ai-career-agent.ru` with production-grade transactional delivery, SPF, DKIM, DMARC, bounce/complaint handling and reputation monitoring.
- Phone/OTP identity is explicitly outside AUTH-001.

## 6. Rollback

Application revert remains safe. Keep additive schema `20260810_0008` after real accounts exist. Downgrade requires verified backup plus explicit approval to lose auth rows/fields. Never remove users, tokens or sessions as part of a routine rollback.

## 7. Следующее действие

```text
AUTH-001 COMPLETE
-> AUTH-002 READY TO START
-> bind HeadHunter/SuperJob OAuth identities to first-party User
```

The domain-sender migration remains a mandatory pre-release infrastructure/delivery gate and does not reopen AUTH-001.

## 8. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Создана candidate verification matrix AUTH-001. |
| 1.1 | 11.08.2026 | Safari CSRF pass подтверждён; Yandex anti-spam blocker зафиксирован; Mail.ru implicit SSL/TLS candidate ожидает CI/Render E2E. |
| 1.2 | 11.08.2026 | v1.4.15 CI/readiness green; Render Free SMTP egress blocker зафиксирован; Gmail API HTTPS candidate добавлен и ожидает CI/Render E2E. |
| 1.3 | 11.08.2026 | Green GitHub Actions, Gmail API readiness/delivery и полный production AUTH E2E подтверждены; AUTH-001 переведён в ВЫПОЛНЕНО, AUTH-002 готов к старту. |
