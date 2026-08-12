# AI Career Agent — extraction reference PROF-002

| Поле | Значение |
|---|---|
| Документ | PROF002_EXTRACTION_REFERENCE |
| Пакет | PROF-002 |
| Версия | 1.0 |
| Дата | 12 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Extractor | `deterministic-text-v1` |

## 1. Contract purpose

Reference определяет контракт предложений PROF-002. Proposal не является confirmed profile, AI output, provider profile mirror или публичным API.

## 2. Input contract

- Один PDF.
- Valid `%PDF` signature.
- Existing configured upload/page/text bounds.
- Text layer обязателен.
- Password-protected and image-only PDF fail closed.
- Full bytes/text live only during request.

## 3. Proposal contract

```text
ResumeImportProposal
- filename             display only; never token/provenance/log
- page_count           aggregate
- character_count      aggregate
- payload              merged editable form values
- extracted_payload    extractor suggestions before merge
- signals              path + confidence + bounded source excerpt
- section_confidence   high | medium | low
- warnings             static review guidance
- conflicts            current scalar vs suggested scalar
- detected_sections    bounded section codes
```

## 4. Supported facts

Best-effort suggestions:

- headline and summary;
- email, phone, Telegram, portfolio/professional URLs;
- current location;
- skills;
- employment rows with company/position/date/description;
- achievements;
- education;
- languages and approximate CEFR level.

Salary, relocation, employment type and work format remain current/default unless safely supplied through future explicit extraction rules.

## 5. Confidence semantics

- `high`: explicit section or strong format match;
- `medium`: known keyword/pattern outside explicit section;
- `low`: weak heuristic, must be checked.

Confidence is not truth probability, candidate quality, employability or AI score.

## 6. Merge semantics

Scalar:

```text
suggestion empty -> keep current
current empty -> show suggestion
current == suggestion -> keep current
current != suggestion -> keep current + show conflict
```

Lists/rows merge unique values using case-insensitive stable keys. Merge never deletes current confirmed facts. User can delete/change anything in review before confirm.

## 7. Confirmation semantics

Only `/profile/import/confirm` creates canonical facts. The submitted form passes ordinary PROF-001 validation, canonical JSON/hash, optimistic expected version and immutable history rules.

No-op confirm does not create a duplicate version.

## 8. Provenance contract

Confirmed import version stores only:

```json
{
  "schema_version": 1,
  "extractor_version": "deterministic-text-v1",
  "page_count": 2,
  "character_count": 6420,
  "detected_sections": ["core", "skills", "employment"],
  "section_confidence": {"core": "medium", "skills": "high"},
  "reviewed_at": 1786530000
}
```

No filename, content, excerpt, email, phone or profile facts are stored in provenance.

## 9. Review token contract

Token is signed and timed. It includes only bounded metadata, HMAC owner fingerprint and base profile version. It is not encrypted storage for the proposal. TTL: 30 minutes.

## 10. Failure semantics

- no text/signals -> `400` with neutral guidance;
- invalid/expired/foreign token -> `400`;
- stale base profile version -> `409`;
- unsupported/oversized input -> `400/413`;
- no implicit fallback to OCR/AI/provider data.

## 11. Future compatibility

OCR and AI parser may later produce the same proposal/review contract, but still cannot bypass explicit user confirmation. Any new source kind or provenance schema requires a migration and updated reference.

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 12.08.2026 | Определены input/proposal/confidence/merge/confirmation/provenance/token contracts PROF-002. |
