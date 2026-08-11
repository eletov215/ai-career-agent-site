# AI Career Agent — security reference AUTH-001

| Поле | Значение |
|---|---|
| Документ | AUTH001_SECURITY_REFERENCE |
| Пакет | AUTH-001 |
| Версия | 1.3 |
| Дата | 11 августа 2026 |
| Статус | ВЫПОЛНЕНО |

## 1. Identity boundary

`users` — единственный first-party identity root. AUTH-001 не присваивает существующие HH/SuperJob OAuth connections новому User. Такое связывание выполняет AUTH-002 только после explicit authenticated consent и migration policy.

## 2. Сохраняемые данные

| Сущность | Данные | Не хранится |
|---|---|---|
| User | email, normalized email, display name, status, verification/password/login timestamps, password hash | plaintext password |
| AuthSession | user id, token hash, created/last-seen/expiry/revoke timestamps, safe reason, user-agent hash | raw token, IP, full user-agent |
| AuthToken | user id, purpose, token hash, TTL, consumed state/reason | raw verification/reset token |
| Email transport config | SMTP/Gmail OAuth secrets in environment only | Git/ZIP/database/log output |

## 3. Password contract

```text
scheme   aca_scrypt
version  1
N        32768
r        8
p        1
salt     16 random bytes
digest   32 bytes
maxmem   64 MiB
```

Stored parser accepts only bounded known costs. `hmac.compare_digest` is used. A fixed-salt dummy hash equalizes unknown-user work and is not a credential.

## 4. Opaque token contract

Raw session/action tokens are `secrets.token_urlsafe(32)` and have at least 256 bits source entropy. Persistence stores SHA-256 only. Database leakage alone does not expose immediately usable tokens. Verification/reset tokens are purpose-bound, expiring, superseded by a newer token and consumed once.

## 5. Session contract

- Absolute TTL default: 12 hours.
- Browser cookie remains `Secure`, `HttpOnly`, `SameSite=Lax` under SEC-001.
- Login rotates Flask session state and preserves only independent provider identity keys.
- Every request loads token hash from PostgreSQL; revoked/expired/inactive-user session is rejected.
- `last_seen_at` writes are throttled to one update per 5 minutes.
- Reset revokes all first-party sessions atomically.

## 6. Enumeration and redirect safety

Register and forgot/reset return generic copy regardless of account existence. Login uses one public failure for unknown, wrong-password, pending, disabled and unverified cases. Resend verification is available as an independent generic form. `next` allows only local absolute paths and rejects scheme/netloc, protocol-relative, backslash and control characters.

## 7. Email contract

Email delivery remains provider-neutral. SMTP adapter supports STARTTLS and implicit SSL/TLS with default certificate validation. Gmail API staging adapter uses HTTPS only, exchanges the environment-stored refresh token for a short-lived access token and sends RFC 2822/base64url messages through `users.messages.send`; permanent access tokens are not stored. Production refuses `memory`; SMTP plaintext/conflicting secure modes remain rejected. Delivery logs include only safe event/purpose/backend/error type and, for Gmail API failures, safe stage/status code; recipient, subject/body, action URL, SMTP responses, OAuth client secret, refresh token and access token are excluded.

Gmail API is explicitly staging-only. Before beta/commercial release, email delivery must move to a project-owned domain sender (target example `noreply@ai-career-agent.ru`) with SPF/DKIM/DMARC and production-grade transactional operations. The transport swap must not change registration/verification/reset business logic.

## 8. HTTP controls

All state changes are POST + CSRF. Route-specific rate limits supplement SEC-001 defaults. Auth responses are no-store and use `Referrer-Policy: strict-origin`: token path/query data is not forwarded, while same-origin HTTPS form POSTs retain the origin required by Flask-WTF strict CSRF validation. Templates use CSRF tokens and no third-party auth-page resources.

## 9. Known residual risks

- In-memory rate limits are not shared across future replicas.
- Google Auth Platform Testing may expire/revoke the staging refresh token and require re-authorization; this is acceptable only for current staging.
- Gmail API sender is temporary staging infrastructure; production domain sender, SPF/DKIM/DMARC, bounce/complaint handling and reputation operations remain a mandatory pre-release gate.
- User-agent hash does not create a human-readable device label.
- MFA, breached-password API, WebAuthn and security notifications are future work.
- Data retention/account deletion belong to PRIV-001.

## 10. Rollback and incident response

Revoke sessions and disable email delivery first. Preserve auth tables for forensic/rollback unless explicit data erasure is required. Rotate/revoke the active provider credentials (SMTP password or Gmail OAuth client/refresh token) if exposed. Token/password plaintext is not expected in logs; any evidence of leakage blocks release and triggers SEC/OPS incident handling.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Зафиксированы password/token/session/email/enumeration/redirect security contracts AUTH-001. |
| 1.1 | 11.08.2026 | Email transport contract расширен STARTTLS + implicit SSL/TLS с запретом plaintext/conflicting modes в production. |
| 1.2 | 11.08.2026 | Добавлен Gmail API HTTPS staging contract, OAuth-token secrecy и обязательный domain-sender migration gate до beta/commercial release. |
| 1.3 | 11.08.2026 | Security controls production-verified: one-time verification/reset, revocable sessions, reset invalidation and Gmail API secret boundaries confirmed; AUTH-001 complete. |
