# AI Career Agent — реестр канонических документов

| Поле | Значение |
|---|---|
| Выпуск / дата | 1.6.4 / 22 сентября 2026 |
| Основа кода | baseline `f5ce1f42836e3872854332324f2ebdd9c8934b36`; LEGAL-001 candidate `fe3a7e1b553ccc9ebb5b956efce3779287291c04` |
| Статус | ДЕЙСТВУЮЩИЙ; LEGAL-001 IMPLEMENTED + CI_PASS; real-data AI CLOSED |

## 1. Активные документы

| Документ | Версия | Область |
|---|---|---|
| PLAN_CURRENT | 1.6.4 | Полный план с сохранённой историей |
| PROJECT_PASSPORT | 2.79 | Полный паспорт с сохранённой историей |
| SOURCE_AUDIT / CANONICAL_DOCUMENTS | 1.6.4 | Источники, очередь, реестр |
| AI005_ACCEPTANCE_SUMMARY | 1.0 | Приёмка только документной части r1 |
| AI005_IMPLEMENTATION / AI005_RUNBOOK / AI005_VERIFICATION_STATUS | 2.0 | Технический r2 и границы проверки |
| AI005_SCOPE / AI005_DELIVERY_GUIDE | 2.0 | Объём и порядок передачи |
| NEXT_PACKAGE_PREPARATION | 1.5 | LEGAL-001 CI_PASS → merge/deploy/QA → owner legal decisions → only then real-data test |

| LEGAL001_SCOPE / IMPLEMENTATION / RUNBOOK / VERIFICATION_STATUS | 1.0 candidate | Versioned consent, withdrawal, admission, privacy, CI evidence |

## 2. Форматы и доказательства

Markdown — текстовый первоисточник. Соответствующие DOCX и PDF сформированы по DOCUMENT_STANDARD1.3; фактический состав форматов указывается в FILE_INDEX.json общего комплекта. Полные план и паспорт не заменены краткими резюме. Предыдущие пакетные документы r1 сохранены в docs/history/ai005-r1.

Приёмка r1: evidence/ai-005-r1-acceptance/acceptance.json и ci285_verified_summary.json. Технический r2: отдельные change_boundary и baseline_files_sha256, результаты локальных тестов. Старое evidence/ai-005 не переписано под новые результаты.

GitHub CI #304 on `fe3a7e1b553ccc9ebb5b956efce3779287291c04` is SUCCESS. LEGAL-001 is `IMPLEMENTED + CI_PASS`; paid provider calls 0; real-data Alice CLOSED. Deployment/production QA/acceptance are not inferred from CI.

## 3. Статусы и распространение

Полный AI-005 остаётся IN_PROGRESS / LIVE_NOT_ACCEPTED. Локальный технический выпуск не является новым GitHub CI или публичным разрешением real-data. PATCH и FULL альтернативны; накладывать старые AI/JOB FINAL PATCH поверх r2 нельзя. Полный состав изменений и SHA-256 выдаются с архивами.

## Исторический снимок предыдущей версии / 17 сентября 2026

Следующий текст сохранён полностью как история; актуальный статус и очередность заданы выше.

# AI Career Agent - Canonical documents / 1.6.2

| Field | Value |
|---|---|
| Date | 2026-09-17 |
| Full package | AI-005 IN_PROGRESS |
| Delivery | r1 NEEDS_VERIFICATION; LIVE_NOT_ACCEPTED |
| Base / candidate schema | 0019 / 0020 |

## 1. Active inventory

PLAN_CURRENT1.6.2, PROJECT_PASSPORT2.77, SOURCE_AUDIT1.6.2, ROADMAP1.6.2, NEXT_PACKAGE_PREPARATION1.3, this registry, AI005_SCOPE/IMPLEMENTATION/RUNBOOK/VERIFICATION_STATUS1.0 and AI005_DELIVERY_GUIDE1.0. Markdown is authoritative. Distribution inventory records which documents have PDF/DOCX counterparts; no uncreated format is claimed. Full plan/passport histories are retained.

## 2. Scope and provenance

AI-005 full feature IN_PROGRESS; r1 document workflow NEEDS_VERIFICATION; LIVE_NOT_ACCEPTED. The latest uploaded JOB-001 canonical ZIP1.6.1 overrides old standalone AI-004 PDFs. Its ten Markdown sources match the preserved closure; __MACOSX metadata is excluded. GitHub main c095bfb is the exact code baseline; unpublished JOB-001 closure docs/guards are carried forward. Existing acceptance JSON is historical and not rewritten to claim new tests.

## 3. Distribution and verification

The new PATCH is against exact current main, not the locally closed predecessor. FULL must match PATCH applied to that base. No remote publication/deployment/new CI is claimed. No old FINAL PATCH should be overlaid after AI-005. Refer to AI005_RUNBOOK for backup before candidate0020 and coordinated rollback. PDF/DOCX exports are convenience versions, not evidence of live AI readiness.

## 4. Historical predecessor (unchanged dated source)

The following reflects the previous release. It does not override the active sections above.

# AI Career Agent - canonical document registry / JOB-001 closure

| Field | Value |
|---|---|
| Release | 1.6.1 / 2026-09-17 |
| PLAN_CURRENT / SOURCE_AUDIT / ROADMAP | 1.6.1 |
| PROJECT_PASSPORT | 2.76 |
| JOB001 implementation / runbook / verification | 1.2 FINAL; ВЫПОЛНЕНО / COMPLETE |
| JOB001 acceptance summary | 1.0 FINAL |
| NEXT_PACKAGE_PREPARATION | 1.2; JOB-001 dependency satisfied, AI-005 not started |
| Accepted application / schema | `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c` / 20260917_0019 |
| LEGAL-001 | Existing decision unchanged; deferred |

## 1. Active release inventory

The bundle provides10 matching Markdown/DOCX/PDF document triples listed in FILE_INDEX.json. Full PLAN_CURRENT and PROJECT_PASSPORT histories are preserved. README and CHANGELOG are synchronized in the code delta. JOB001_RECONSTRUCTION remains dated lineage. The shared export follows DOCUMENT_STANDARD1.3; historical AI and legal evidence is unchanged.

## 2. Evidence and publication

Recorded acceptance is based on mainCI283 and owner-confirmed final browser/log checks. evidence/job-001/acceptance.json and ci283_verified_summary.json preserve identifiers and separate sources. closure_checks.json reports only newly executed local checks. New remote CI for this final documentation/status-guard update is NOT RUN until publication. No runtime code, schema or deployment is changed by document creation.

Manual isolation is NOT RUN due to the explicitly absent second account. Legacy transfer and second-device subcases have no separate confirmed outcome. Actual Neon backup/restore is not evidenced. Full public/live AI, email delivery and LEGAL-001 remain open. Older AI acceptance evidence, provider policy and legal decisions remain unmodified.

## 3. Distribution and rollback

The canonical bundle includes10 matching document triples, source evidence, FILE_INDEX and SHA-256. The code PATCH is based on exact accepted main and lists all changes; FULL is its equivalent complete snapshot. Do not overlay older AI-004/JOB-001 patches afterwards. These artifacts are local, not an assertion of a changed GitHub main. Reverting this documentation-only closure needs no migration; runtime rollback is separately specified in JOB001_RUNBOOK.

## 4. Next action and version history

Next in the approved sequence is AI-005. Its saved-vacancy prerequisite is satisfied; feature design and live/legal activation remain separate. 1.6.1 records JOB-001 acceptance; 1.6.0 records the reconstructed candidate and approved ordering; 1.5.7 remains the historical AI-004 closure.
