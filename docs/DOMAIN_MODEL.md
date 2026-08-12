# AI Career Agent — domain model

## Identity foundation

```text
User
  1 -> many AuthSession
  1 -> many AuthToken
  1 -> 0..1 OAuthConnection per provider
```

AUTH-001/002 remain completed.

## PROF-001

```text
User 1 -> 0..1 CareerProfile
CareerProfile 1 -> many CareerProfileVersion
```

### CareerProfile

Current owner-confirmed state:

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

### CareerProfileVersion

Immutable evidence:

```text
id, profile_id
schema_version, version
snapshot_json
content_hash
changed_sections_json
created_at
```

Constraint: unique `(profile_id, version)`, FK cascade from current profile.

## Ownership semantics

All repository operations resolve through `user_id`. Version lookup joins current profile owner. No provider email/external ID or profile content is used as an ownership key.

## Confirmation semantics

A saved profile means the authenticated owner submitted the canonical form. Missing values remain null/empty. Provider snapshots, PDF extraction and AI output are not confirmed facts.
