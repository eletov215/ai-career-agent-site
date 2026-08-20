# AI Career Agent — domain model

## Identity foundation

```text
User
  1 -> many AuthSession
  1 -> many AuthToken
  1 -> 0..1 OAuthConnection per provider
  1 -> 0..1 CareerProfile
  1 -> many ResumeDraft
```

AUTH-001/002 and PROF-001 remain completed.

## CareerProfile

Current owner-confirmed structured facts:

```text
id, user_id
schema_version, version
headline, summary
contacts_json, goals_json, geography_json, salary_json
skills_json, employment_json, achievements_json
education_json, languages_json
content_hash, completion_percent
confirmed_at, created_at, updated_at
```

Constraints: unique `user_id`, version/schema >= 1, completion 0..100, FK cascade from User.

## CareerProfileVersion

Immutable evidence of each material confirmed change:

```text
id, profile_id
schema_version, version
snapshot_json, content_hash
changed_sections_json
source_kind             manual | resume_import
provenance_json         bounded aggregate metadata
created_at
```

Constraints: unique `(profile_id, version)`, version/schema >= 1, controlled source kind. Snapshot remains full canonical PROF-001 schema version 1.

## PROF-002 proposal model

`ResumeImportProposal` is a request-scoped domain value, not a persistence entity:

```text
filename (display only)
page_count / character_count
payload / extracted_payload
signals(path, confidence, bounded excerpt)
conflicts(path, current, suggested)
section_confidence / warnings / detected_sections
```

The proposal and raw resume text are never stored. It becomes canonical only after owner-confirmed form submission.

## Resume import provenance

A confirmed `resume_import` version may store only:

```json
{
  "schema_version": 1,
  "extractor_version": "deterministic-text-v1",
  "page_count": 2,
  "character_count": 6400,
  "detected_sections": ["core", "skills"],
  "section_confidence": {"core": "medium", "skills": "high"},
  "reviewed_at": 1786530000
}
```

Filename, raw text, contacts, excerpts and profile payload are forbidden.

## Ownership and version semantics

- owner is authenticated first-party `User.id`;
- review token is owner/version-bound but not a database record;
- confirm uses current owner profile row lock;
- stale base version fails with controlled conflict;
- version numbers remain owner-relative;
- no-op confirmation creates no duplicate version.

## PROF-003 entities

- `ResumeDraft`: mutable current owner-scoped document, revision/hash/completion.
- `ResumeVersion`: immutable snapshot; reason `checkpoint|export|restore`.
- `ResumeAsset`: owner/draft-scoped photo or university logo bytes with MIME/size/SHA-256.
- `ResumeExport`: metadata linking a client-generated PDF to an immutable version.

Deleting a draft cascades its versions/assets/export metadata. PROF-001 remains the confirmed-facts root.


## PRIV-001 privacy audit model

`PrivacyAuditEvent` is intentionally **not** an owner-scoped child of `User`:

```text
PrivacyAuditEvent
  id
  event_type      data_exported | account_deleted | retention_cleanup
  counts_json     bounded aggregate counts only
  created_at
```

The absence of `user_id`, email, filename, asset ID and content is a data-minimization property: after account deletion the audit row proves an operation occurred without retaining a direct account identifier. Active owner data continues to live in the existing Auth/OAuth/Profile/Resume models and is exported/deleted through `PrivacyService`.

## SourceHealthState
Owner-independent current operational state for one canonical vacancy provider. No User/OAuth relation; no secret or PII columns.
