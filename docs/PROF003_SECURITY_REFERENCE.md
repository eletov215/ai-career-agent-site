# AI Career Agent — security reference PROF-003

| Поле | Значение |
|---|---|
| Документ | PROF003_SECURITY_REFERENCE |
| Пакет | PROF-003 |
| Версия | 1.2 |
| Дата | 13 августа 2026 |
| Статус | ВЫПОЛНЕНО |

## 1. Security boundary

First-party User + active server-side AuthSession — единственная browser authentication boundary. Resume text, PDF hash, image or PROF-001 snapshot не являются identity proof.

## 2. Data lifecycle

```text
browser editor state
-> bounded JSON + expected revision
-> owner-scoped row lock
-> mutable current draft
-> explicit checkpoint/export/restore
-> immutable version
```

Images:

```text
processed browser image
-> bounded multipart upload
-> MIME/signature validation
-> owner/draft-scoped durable asset
-> UUID in draft/version state
```

## 3. Access controls

- all routes require verified first-party session;
- draft/version/export reachable only through owner scope;
- asset requires matching `user_id`;
- saving an asset reference additionally checks same draft and kind;
- foreign resources return neutral `404`.

## 4. Mutation controls

- JSON/multipart/form POST/PUT protected by CSRF;
- per-route rate limits;
- `expected_revision` prevents stale overwrite;
- PostgreSQL row lock serializes material update/checkpoint/export/restore;
- immutable version rows have no update route;
- delete is owner-only and cascades only that draft subtree.

## 5. Resource controls

- generic body limit plus upload-route classification;
- state max 160 KiB;
- bounded messages/field lengths;
- processed image max 2 MiB;
- MIME + magic signature check;
- PDF metadata bounds; no PDF binary accepted;
- UUID references and canonical JSON/hash.

## 6. Logging and privacy

Allowed telemetry:

```text
changed
draft_revision
completion_percent
resume_version
version_created
reason
asset_kind
asset_bytes
page_count
pdf_bytes
```

Forbidden:

```text
answers/messages/full state/snapshot
photo/logo bytes
asset IDs or user IDs
PDF filename/hash
contacts
cookies/session token
```

## 7. Threats and controls

| Threat | Control |
|---|---|
| cross-user read/write | owner-scoped joins + active session |
| lost update | expected revision + row lock + `409` |
| CSRF | Flask-WTF token |
| state/resource exhaustion | body/state/field/message/image bounds |
| malicious image | MIME + signature + no server image execution |
| foreign asset injection | owner + draft + kind reference validation |
| version tampering | immutable snapshots + owner-only history |
| fact laundering | draft/profile separation; no reverse auto-sync |
| ephemeral filesystem loss | PostgreSQL persistence; no local file path |
| PDF leakage | binary remains client-side; metadata only |

## 8. Production security evidence

- owner isolation for draft/history/version was confirmed with User A/User B;
- stale parallel-tab overwrite was rejected and newer state survived;
- iPhone photo asset survived refresh/relogin/cross-device and Render restart;
- hotfix r1 removed a logging-key runtime failure without adding resume content to logs;
- r2-r4 did not change owner/revision/CSRF/database schema boundaries.

Final Render log review after r4 confirmed absence of new 500/Traceback/migration errors and sensitive resume/session payload. PROF-003 COMPLETE.

## 9. Residual risks

- Browser displays personal resume data during editing.
- PostgreSQL BLOB storage increases backup/database volume.
- In-memory rate limit remains a single-instance staging limitation.
- No collaborative merge; stale edits require reload.
- Legacy localStorage remains readable until one-time migration/removal.
- External object storage requires a future credentials/encryption/retention threat model.

## 10. Incident response

Stop affected routes, revoke sessions if browser identity is suspect, preserve encrypted backup, inspect secret-free events, verify owner scopes and follow SEC/OPS incident procedure. Resume content should not be present in logs.

## 11. Rollback

Application revert may retain `0012`. Controlled downgrade deletes PROF-003 data; never run automatically. Restore from verified backup if rollback must preserve drafts.

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Defined owner/revision/CSRF/resource/asset/version/export/logging and rollback controls. |
| 1.1 | 13.08.2026 | Added production owner/stale/asset/restart evidence and final log-review closure requirement; r1-r4 preserve security/schema boundaries. |
| 1.2 | 13.08.2026 | Final regression `/profile`/PROF-002/`/dashboard`/AUTH/OAuth/`/vacancies`, readiness `0012` and Render log privacy/error review confirmed; PROF-003 COMPLETE, PRIV-001 next. |
