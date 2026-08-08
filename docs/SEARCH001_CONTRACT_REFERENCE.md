# AI Career Agent — SEARCH-001: справочник контракта вакансии

| Поле | Значение |
|---|---|
| Документ | SEARCH001_CONTRACT_REFERENCE |
| Версия | 1.0 |
| Дата | 08 августа 2026 |
| Пакет | SEARCH-001 |
| Статус | ДЕЙСТВУЮЩИЙ ДЛЯ CANDIDATE |
| Contract version | 1 |
| Связанный план | PLAN_CURRENT 1.4.5 |

## 1. Контрольный статус

Справочник описывает contract candidate SEARCH-001. Значения становятся production contract после завершения GitHub/Render verification.

## 2. Поля NormalizedVacancy

| Поле | Тип | Правило |
|---|---|---|
| external_id | str | stable provider ID; empty допустим только для defensive legacy mapping, не для новой source row |
| source | str | lowercase provider key |
| source_title | str | display name источника |
| title/company/location | str | cleaned display text |
| salary_from/salary_to | float or null | positive values; invalid/zero -> null; lower <= upper |
| currency | str | uppercase ISO-like code, aliases normalized |
| work_format | canonical code | explicit conservative mapping |
| employment_code | canonical code | explicit conservative mapping |
| experience_code | canonical code | explicit conservative mapping |
| schedule/employment/experience | str | provider display labels |
| description/requirements | str | plain cleaned text |
| published_at/source_modified_at | UTC ISO or null | `YYYY-MM-DDTHH:MM:SSZ` |
| url | str | source link |
| source_status | active or closed | lifecycle |
| closed_reason | str or null | bounded reason label |
| closed_at | int or null | epoch used by existing lifecycle storage |
| contract_version | int | currently 1 |

## 3. Canonical work_format

| Code | Meaning | Mapping policy |
|---|---|---|
| remote | Fully remote | explicit remote field/ID/label only |
| hybrid | Hybrid | explicit hybrid evidence |
| onsite | On-site | explicit office/on-site evidence; never inferred from `remote=false` alone |
| field | Field/travelling | explicit field/travel evidence |
| fly_in_fly_out | Rotation/вахта | explicit rotation evidence |
| unknown | Not reliably known | default |

## 4. Canonical employment_code

| Code | Meaning |
|---|---|
| full | Full-time/full employment |
| part | Part-time |
| project | Project/contract role |
| temporary | Temporary/seasonal |
| probation | Internship/probation |
| volunteer | Volunteer |
| shift | Shift employment |
| side_job | Side job/podrabotka |
| unknown | Not reliably known |

## 5. Canonical experience_code

| Code | Meaning |
|---|---|
| no_experience | No experience required |
| between_1_and_3 | 1–3 years |
| between_3_and_6 | 3–6 years |
| more_than_6 | More than 6 years |
| unknown | Not reliably known |

## 6. Currency, salary and date policy

- `RUR` becomes `RUB`; `BYR` becomes `BYN`.
- Unknown/empty currency stays empty, not RUB by default.
- Zero/negative/non-finite salary means not specified.
- Reversed ranges are ordered without inventing missing bounds.
- Epoch or ISO timestamps are converted to UTC `Z`; invalid values become null.

## 7. Provider adapter boundary

```text
raw provider payload
→ provider adapter
→ NormalizedVacancy
→ common filter / persistence / presenter
```

Provider-specific request parameters remain in adapters, but application filtering and storage use canonical fields.

## 8. Legacy compatibility

- `remote: bool` remains a derived compatibility field: true only for `work_format=remote`; hybrid is not remote.
- DB canonical fields are nullable for legacy rows.
- Repository textual fallback is allowed only when the corresponding canonical column is null.
- Refreshed rows are rewritten through the central normalizer.

## 9. Exclusions

No cross-source fingerprint/fuzzy merge, no global pagination redesign and no deletion of raw labels in SEARCH-001.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 08.08.2026 | Зафиксирован SEARCH-001 contract version 1 |
