# AI Career Agent — security reference PROF-002

| Поле | Значение |
|---|---|
| Документ | PROF002_SECURITY_REFERENCE |
| Пакет | PROF-002 |
| Версия | 1.0 |
| Дата | 12 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Security boundary

First-party User + active server-side AuthSession остаются единственной browser authentication boundary. Resume PDF не является identity proof и не меняет ownership.

## 2. Data lifecycle

```text
request upload bytes
-> bounded pypdf text extraction
-> in-memory proposal
-> HTML review form
-> explicit confirm
-> canonical profile snapshot + aggregate provenance
```

Bytes, raw text and unconfirmed proposal are not persisted by PROF-002.

## 3. Upload controls

- global and route size limits;
- extension + PDF signature validation;
- page/text bounds;
- encrypted/image-only handling fail closed;
- safe basename for display only;
- no external URL fetch or OCR process.

## 4. Review token controls

- `itsdangerous` timed signature;
- dedicated salt;
- 30-minute TTL;
- HMAC owner fingerprint instead of raw User ID;
- base profile version binding;
- no filename/text/facts in payload;
- tamper/foreign/expired failure is neutral.

## 5. Confirmation controls

- POST + CSRF + active first-party session;
- owner-bound token validation;
- expected version equality;
- PROF-001 validation and PostgreSQL row lock;
- immutable version + source/provenance in one transaction;
- no silent replacement of existing scalar facts.

## 6. Logging and privacy

Allowed telemetry:

```text
page_count
character_count
detected_section_count
conflict_count
changed
profile_version
completion_percent
```

Forbidden:

```text
filename
raw/extracted text
source excerpt
contacts
proposal or confirmed snapshot
signed token
owner/user ID
cookies/session token
```

## 7. Threats and controls

| Threat | Control |
|---|---|
| cross-user confirmation | owner HMAC fingerprint + first-party session |
| stale overwrite | base version + PROF-001 row lock/conflict |
| CSRF | Flask-WTF token |
| malicious non-PDF | extension/signature/parser validation |
| oversized resource use | body/page/text bounds |
| fact laundering | proposal/review distinction + explicit confirm |
| silent confirmed-value overwrite | conflict-preserving merge |
| data leakage in token/log | metadata-only token and secret-free events |
| history traversal | existing owner-scoped PROF-001 routes |

## 8. Residual risks

- Parser errors can still mis-suggest facts; review is mandatory.
- Browser form contains unconfirmed personal data during review.
- In-memory rate limiting remains a single-instance staging limitation.
- No persisted draft means browser refresh loses review.
- OCR/AI additions need a separate threat model.

## 9. Incident response

For suspected exposure: stop import route, revoke sessions, inspect secret-free events, rotate Flask secret if signed token integrity is in doubt, preserve DB backup and follow SEC/OPS incident procedure. Raw resume text should not exist in DB or logs under this contract.

## 10. Rollback

Application revert may retain `0011`. Controlled downgrade removes provenance columns only. Do not delete confirmed snapshots or restore automatic import.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 12.08.2026 | Зафиксированы upload lifecycle, owner/token/version controls, privacy/logging and rollback contracts PROF-002. |
