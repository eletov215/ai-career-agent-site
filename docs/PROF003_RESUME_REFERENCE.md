# AI Career Agent — resume contract reference PROF-003

| Поле | Значение |
|---|---|
| Документ | PROF003_RESUME_REFERENCE |
| Пакет | PROF-003 |
| Версия | 1.2 |
| Дата | 13 августа 2026 |
| Статус | ВЫПОЛНЕНО |
| Draft schema | 1 |

## 1. Contract purpose

Reference определяет server-side document draft/version contract. ResumeDraft — редактируемое представление документа, а не canonical confirmed career profile, AI output или public API guarantee.

## 2. Ownership

```text
draft.user_id == authenticated first-party User.id
version reachable only through owner-scoped draft join
asset.user_id == owner and asset.draft_id == current draft
export reachable only through owner-scoped draft/version
```

## 3. Canonical draft state

```json
{
  "schemaVersion": 1,
  "index": 0,
  "answers": {
    "name": "",
    "role": "",
    "experience": "",
    "achievements": "",
    "skills": "",
    "education": "",
    "contacts": "",
    "goal": ""
  },
  "messages": [],
  "photoAssetId": null,
  "universityLogoAssetId": null,
  "universityLogoFor": "",
  "universityResolvedName": ""
}
```

Unknown keys/values fail validation; they are not guessed.

## 4. Bounds

- state JSON: max 160 KiB;
- 8 known answer fields with field-specific limits;
- messages: max 40, each max 5000 chars, type `ai|user`;
- title: max 160;
- photo: JPG/PNG/WebP; university logo additionally allows validated GIF/ICO; max processed asset 2 MiB;
- PDF export metadata: 1..100 pages, 1 byte..50 MiB, lowercase SHA-256, filename max 255.

## 5. Current revision semantics

- create starts at revision 1;
- material state hash change increments revision;
- no-op autosave keeps revision;
- expected revision mismatch fails `409`;
- automatic field-level merge is absent.

## 6. Immutable version semantics

```text
version unique within draft
snapshot_json + content_hash immutable
reason checkpoint | export | restore
restored_from_version only for restore
```

Checkpoint/export with same latest hash reuses latest version. Restore writes historical snapshot into current draft and creates a new immutable version.

## 7. Profile relationship

Creating a draft from PROF-001 copies current confirmed facts into document fields and records only `profile_version` as seed metadata. Later draft edits never mutate PROF-001. AI features must use explicit proposal/confirmation contracts rather than laundering document text into confirmed facts.

## 8. Asset contract

State stores only asset UUID. Bytes live in ResumeAsset. Asset must belong to same owner, draft and expected kind. Historical versions remain renderable while draft exists because referenced assets are retained until draft deletion.

## 9. Export contract

Browser export is generated from the same paginated preview after save flush. Server stores only immutable version link and metadata; no PDF binary. Export metadata does not prove visual correctness by itself, so preview/PDF parity remains a manual/automated E2E gate.

## 10. Production UI/export compatibility

- Direct editor r2 mutates the same eight canonical `answers` fields and uses ordinary autosave/revision semantics; it does not create a second state model.
- iPhone photo hotfix r3 changes only browser dataURL-to-Blob conversion; server asset contract is unchanged.
- PDF/logo hotfix r4 changes rendering only: `universityResolvedName` remains the heading source and exact normalized duplicate detail may be hidden; canonical draft state is unchanged.

## 11. Legacy localStorage

Legacy state may be read once and migrated through normal server validation. After successful server save the legacy key is removed. New authoritative writes never use localStorage.

## 12. Future compatibility

New document fields require schema versioning/defaults. External object storage may replace binary repository implementation without changing UUID references. AI interview, templates and public sharing require separate contracts.

## 13. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Defined owner, current revision, immutable versions, assets, export metadata and profile-seed boundaries. |
| 1.1 | 13.08.2026 | Added production compatibility note for direct edit r2, Safari asset r3 and PDF/logo rendering r4; canonical state/schema unchanged. |
| 1.2 | 13.08.2026 | Final regression `/profile`/PROF-002/`/dashboard`/AUTH/OAuth/`/vacancies`, readiness `0012` and Render log privacy/error review confirmed; PROF-003 COMPLETE, PRIV-001 next. |
