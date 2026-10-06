# AUTH production email gate — 2026-10-06

| Поле | Состояние |
|---|---|
| AUTH-001 business logic | COMPLETE (historical accepted scope preserved) |
| Current staging backend | Gmail API |
| Gmail production suitability | NOT_ACCEPTED / staging-only |
| Owner observation | Verification message currently does not arrive |
| Immediate root cause | NOT_PROVEN by this docs sync |
| Production email readiness | PENDING / P0 before beta-commercial |
| DOMAIN-001 dependency | REQUIRED |
| Email/provider sends in this change | 0 |

## 1. Что принято и что не принято

AUTH-001 already proved the account/token/session/verification/reset business logic and previously completed a real Gmail API staging E2E. Those historical results are not revoked.

They also never approved personal Gmail as commercial infrastructure. Existing repository documents explicitly say:

- Gmail API is staging-only;
- Google Auth Platform Testing may expire/revoke the staging refresh token and require re-authorization;
- before beta/commercial release the sender must move to a project-owned domain with production-grade transactional delivery, SPF/DKIM/DMARC, bounce/complaint handling and reputation operations.

The owner's current report that verification mail is not arriving therefore re-opens **operational production-email readiness**, not the accepted account logic.

## 2. Release gate

Before beta/commercial release the following must all be PASS:

1. `DOMAIN-001` provides the selected project domain and production callback/base-URL configuration.
2. A project-owned sender address is configured.
3. SPF, DKIM and DMARC are configured and verified for the sender domain.
4. A production-grade transactional provider or owned mail infrastructure is selected and documented.
5. Secrets stay outside Git/database/logs.
6. Registration verification email arrives at a normal external mailbox.
7. Resend verification succeeds and supersedes the previous token as designed.
8. Forgot-password email arrives and reset succeeds.
9. Verification/reset tokens remain TTL-bound, one-time and enumeration-safe.
10. Bounce/complaint/reputation operations are documented.
11. Production observability reports delivery stage/status without recipient, action token, provider body or credentials.
12. The final E2E is repeated after the production host/domain cutover.

## 3. Provider decision boundary

This document does not activate a provider and does not create billable resources. A Yandex-hosted transactional option can be evaluated during DOMAIN-001/Stage C account review, but final provider selection requires its own configuration/cost/operational evidence.

Do not keep re-authorizing a personal Gmail Testing refresh token as the commercial design.

## 4. Failure classification

Current owner report: verification mail does not arrive.

Recorded repository risk: the staging Google Testing refresh token may expire/revoke. That makes the staging design unsuitable for production, but this document does **not** claim that token expiry is definitively the current incident root cause without provider/runtime evidence.

No email was sent while preparing this document.
