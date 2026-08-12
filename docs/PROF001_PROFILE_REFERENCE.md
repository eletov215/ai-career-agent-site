# AI Career Agent — profile reference PROF-001

| Поле | Значение |
|---|---|
| Документ | PROF001_PROFILE_REFERENCE |
| Пакет | PROF-001 |
| Версия | 1.0 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Schema version | 1 |

## 1. Contract purpose

Reference defines the manually confirmed structured profile contract. It is not a resume extraction schema, provider profile mirror, AI output or public API guarantee.

## 2. Ownership

```text
profile.user_id == authenticated first-party User.id
one current profile per User
versions reachable only through owner-scoped profile join
```

Provider external IDs/emails do not determine profile ownership.

## 3. Canonical snapshot

```json
{
  "schema_version": 1,
  "headline": null,
  "summary": null,
  "contacts": {
    "contact_email": null,
    "phone": null,
    "telegram": null,
    "portfolio_url": null,
    "linkedin_url": null
  },
  "goals": {
    "target_roles": [],
    "industries": [],
    "employment_types": [],
    "work_formats": []
  },
  "geography": {
    "current_location": null,
    "preferred_locations": [],
    "relocation": "consider"
  },
  "salary": {
    "minimum": null,
    "maximum": null,
    "currency": null,
    "period": "month",
    "tax_mode": "unspecified"
  },
  "skills": [],
  "employment": [],
  "achievements": [],
  "education": [],
  "languages": []
}
```

## 4. Controlled values

Employment types:

```text
full | part | project | temporary | internship
```

Work formats:

```text
onsite | remote | hybrid | flexible
```

Relocation:

```text
not_ready | ready | consider
```

Salary currencies:

```text
RUB | BYN | USD | EUR | KZT
```

Salary period:

```text
month | year | hour
```

Skill level:

```text
unspecified | basic | intermediate | advanced | expert
```

Language level:

```text
unspecified | a1 | a2 | b1 | b2 | c1 | c2 | native
```

## 5. Row contracts

Skill:

```text
name required, max 80
level controlled
case-insensitive unique within snapshot
```

Employment:

```text
company required, max 160
position required, max 160
start/end optional YYYY-MM
current boolean; current clears end
description optional max 2500
end >= start
max 20 rows
```

Achievement:

```text
title required max 180
year optional 1900..current+10
description optional max 2000
max 20 rows
```

Education:

```text
institution required max 200
degree optional max 120
field optional max 160
start/end year optional 1900..current+10
end >= start
description optional max 1500
max 15 rows
```

Language:

```text
name required max 80
level controlled
case-insensitive unique
max 15 rows
```

## 6. General bounds

```text
headline max 160
summary max 4000
target roles max 10 x 120
industries max 10 x 120
preferred locations max 10 x 160
skills max 50
salary 0..1,000,000,000
only http/https URLs; no embedded username/password
```

Empty values normalize to null/empty arrays. Unknown enum values fail validation; they are not guessed.

## 7. Completion indicator

Deterministic informational weights:

| Section | Weight |
|---|---:|
| headline or summary | 10 |
| any contacts | 10 |
| target roles | 15 |
| employment/work format goals | 5 |
| geography | 10 |
| salary | 10 |
| skills | 15 |
| employment | 15 |
| education | 5 |
| languages | 3 |
| achievements | 2 |

Completion is not employability, quality, confidence or AI score and never blocks save.

## 8. Version contract

- current `version` starts at 1;
- full canonical snapshot is SHA-256 hashed;
- same hash means no material change and no new version;
- changed hash increments current version and writes immutable version snapshot in one transaction;
- `changed_sections` is explainability metadata, not a patch;
- stale expected version fails; no implicit merge;
- historical restore is out of scope.

## 9. Source/confirmation semantics

All PROF-001 facts have one source semantic: manually submitted by the authenticated owner. HH/SuperJob metadata, resume extraction and AI suggestions remain external/unconfirmed until a future explicit review flow.

## 10. Privacy and future use

Profile facts are personal data. Future search/AI/document services must consume them through the profile service contract, preserve owner scope and never infer missing values as confirmed facts. PRIV-001 will add export/delete/retention. PROF-002 will add import provenance and editable review.

## 11. Migration compatibility

Schema version is independent of Alembic revision. Additive future fields must remain readable with defaults or use an explicit profile schema migration. Existing version snapshots remain immutable evidence.

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | Defined owner, canonical snapshot, bounds, enums, completion and immutable version semantics. |
