# AI Career Agent — security reference PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_SECURITY_REFERENCE |
| Пакет | PRIV-001 |
| Версия | 1.2 |
| Дата | 19 августа 2026 |
| Статус | ВЫПОЛНЕНО |

## 1. Security boundary

Active first-party User + server-side AuthSession is browser identity. Export additionally re-authenticates current password. Delete requires current password + exact phrase. URLs/export filenames/provider identity are never identity proof.

## 2. Export controls

- login + CSRF + rate limit + current password;
- owner-scoped consistent PostgreSQL snapshot;
- bounded raw/archive size + `SpooledTemporaryFile`;
- safe ZIP paths, `no-store`, no ETag;
- provider-profile sanitizer;
- only owned draft-bound assets; integrity mismatch fails closed;
- explicit secret exclusion tests.

## 3. Delete controls

- login + CSRF + lower rate limit;
- exact phrase and current password;
- password hash recheck under User row lock;
- coordinated User -> Auth -> OAuth lock order;
- explicit legacy HH/SJ mirror cleanup;
- FK cascade owner subtree;
- browser session clear.

## 4. Audit/log minimization

Allowed: `event_type`, bounded aggregate counts, timestamp/random row id, health/status. Forbidden: user/email/provider IDs, filenames/hashes, contacts, profile/resume content, image bytes, export payload, passwords, cookies/session/OAuth tokens.

## 5. Retention controls

Cleanup is bounded and cross-process locked. Orphan ResumeAsset is eligible only after age threshold and only if current/history references are absent after row-lock recheck. Malformed historical state is handled conservatively. Worker heartbeat is non-gating for web readiness.

## 6. Threat matrix

| Threat | Control |
|---|---|
| cross-user export | owner scope + row lock |
| stolen session export | current password |
| credential leak | explicit omission + sanitizer + secret scan tests |
| zip slip/path injection | safe path normalization/hash fallback |
| oversized export | preflight/raw/archive bounds + spooled storage |
| stale password during delete | hash recheck inside locked transaction |
| concurrent reset/OAuth during delete | unified lock order |
| foreign asset injection/corrupt ownership | owner+draft validation, fail closed |
| cleanup deletes historical asset | current/history reference scan + recheck |
| audit re-identification | no direct owner/provider identifiers; bounded aggregates |

## 7. Production evidence

Green CI dedicated gate; Render `0013`; export secret scan/assets; deletion negative/positive/owner isolation; restart/regression; Render Logs free of new application/migration/privacy-worker errors and sensitive payload.

## 8. Residual risks

- remote provider grant revoke absent;
- existing backups are not rewritten by account deletion;
- legal policy/final retention pending;
- large export remains synchronous though bounded/spooled;
- staging memory rate-limit backend is not multi-replica store.

## 9. Incident response

Disable affected route/worker, preserve secret-free evidence and verified backup as appropriate, inspect owner predicates/deploy diff; never request credentials or personal export ZIP.

## 10. Rollback

Schema/app rollback does not resurrect deleted account. Recovery only from verified backup with explicit decision.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Initial export/delete/audit/retention security boundary. |
| 1.1 | 19.08.2026 | Hardened re-auth/snapshot/concurrency/sanitizer/orphan asset controls. |
| 1.2 | 19.08.2026 | External CI/Render/E2E/log evidence confirmed; COMPLETE. |
