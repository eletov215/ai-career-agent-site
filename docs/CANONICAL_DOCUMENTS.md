# AI Career Agent — реестр канонических документов

<!-- HOST001-INCIDENT-20261009:START -->
## HOST-001 Stage C — актуальный статус на 9 октября 2026

> Этот новый блок дополняет прежний successor от 6 октября; исторические записи `NOT_RUN` ниже относятся к более ранней дате и не описывают итог сегодняшних запусков.

- **FIELD TEST: FAILED / NOT_ACCEPTED.** Credentialed plan-only #8 SUCCESS; bounded apply #5 FAILED после успешной регистрации автоматического teardown. Тесты созданного сайта, PG18/TLS, backup/restore и Russia-source остаются NOT_RUN.
- **TEARDOWN: VERIFIED IN TERRAFORM STATE.** Автоматический teardown #7 FAILED до `terraform destroy` из-за необъявленной `SOURCE_RUN_STARTED_AT`; ручной recovery #8 SUCCESS, удаление выполнено, managed resources в Terraform state: **0**.
- **Код исправлен:** PR [#92](https://github.com/eletov215/ai-career-agent-site/pull/92) MERGED; commit `2dc5c715953eefd166e71a9079df727e6bce80ab`, PR-head CI #644 SUCCESS. Исправлены передача времени и безопасная классификация ошибок apply. Это ещё не повторный успешный live-тест.
- **Проверка Yandex Console:** по предоставленным оператором скриншотам списки VM, PostgreSQL и VPC-сетей пусты; отдельная проверка публичных IP не завершена. Хранилище Terraform state оставлено для recovery; показанные 0 ₽ в Billing предварительны.
- **Запреты не изменились:** Render/Neon production, MIG-001, реальные данные, Alice provider calls и отправка email не затрагивались; `REAL_DATA_SUPPORTED=False`.
- **Следующее действие:** закрыть остаточные resource/billing checks и разобраться в первичной причине apply; повторный платный запуск только после отдельного подтверждения бюджета и безопасного плана, без автоматического переноса ранее выданного разрешения.

Доказательства и границы: [HOST001_STAGE_C_INCIDENT_20261009.md](HOST001_STAGE_C_INCIDENT_20261009.md).
<!-- HOST001-INCIDENT-20261009:END -->


<!-- DOC001-SUCCESSOR-20261006:START -->
## Текущий канонический successor / 6 октября 2026

> Этот блок является актуальным successor-состоянием после JOB-004 и infrastructure PR #74/#75. Датированные acceptance-блоки ниже сохраняются без переписывания для historical evidence и package guards.

| Поле | Текущее состояние |
|---|---|
| Current main | `cc12b7de80b73f372aa185fadc1e49f58e9c2817` |
| Schema | `20261002_0023` |
| JOB-004 | COMPLETE; production SITE QA accepted; migration NOT_APPLICABLE |
| HOST/INFRA | Stage B + Stage C preparation merged; Yandex apply/resource creation NOT_RUN |
| Current Render | `dep-db2ekrbncjis73ciogcg` LIVE on current main |
| Stage C field test | NEXT / separate owner approval required; recommended test ceiling remains 500 RUB |
| REED-COMPAT-001 | NEXT inside Russia-hosted field-test window; NOT_RUN |
| Trudvsem | non-blocking diagnostic during Russia field test; foreign-hosting cause NOT_PROVEN |
| DOMAIN-001 | PENDING before beta |
| Production transactional email | P0 pre-release gate / PENDING; AUTH logic remains COMPLETE |
| MIG-001 | NOT_AUTHORIZED / NOT_RUN |
| SRC-001 | restored to explicit pre-release sequence; PLANNED after migration evidence |
| Legal | TECHNICAL_ACCEPTED / LEGAL_PENDING; policy DRAFT / NOT_ACTIVE |
| Real-data Alice | CLOSED; `REAL_DATA_SUPPORTED=False` |

### Активная очередь

1. Stage C — короткий synthetic field test в Yandex Cloud Russia после отдельного owner approval на billable resources.
2. В том же окне — `REED-COMPAT-001` и ограниченное non-blocking наблюдение доступности Trudvsem из России.
3. `DOMAIN-001` + production transactional email gate: project-owned sender/domain, SPF/DKIM/DMARC и полный verification/reset E2E.
4. `MIG-001` — отдельный owner-gated перенос production с rollback/recovery evidence.
5. `SRC-001` — подключение новых источников; Reed является первым конкретным кандидатом только если `REED-COMPAT-001` пройден.
6. Legal activation / controlled real-data AI остаются отдельным gate и могут готовиться параллельно, но real-data AI не открывается автоматически инфраструктурой.
7. `REL-001` — финальная предрелизная проверка MVP 1.0.

### Email boundary

`AUTH-001 COMPLETE` сохраняется как исторически принятая account/token/session/verification business logic. Это **не равно production email readiness**. Personal Gmail API остаётся staging-only. Владелец сообщил, что текущие verification messages больше не приходят; точная причина нынешнего сбоя этим docs-sync не объявляется доказанной. Репозиторий уже фиксирует риск истечения/отзыва Google Auth Platform Testing refresh token. До beta/commercial release обязателен production-grade domain sender и новый E2E.

Актуальные successor-документы: `docs/PACKAGE_REGISTRY_CURRENT.md`, `docs/AUTH_PRODUCTION_EMAIL_GATE_20261006.md`, `docs/HOST001_STAGE_C_FIELD_TEST_PLAN_20261006.md`.
<!-- DOC001-SUCCESSOR-20261006:END -->

| Поле | Значение |
|---|---|
| Выпуск / дата | 1.6.5 / 24 сентября 2026 |
| Основа кода | technical acceptance main `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`, tree `2616a3b15df09f85bf7ae261e605356fb9f52f9d`; production runtime evidence `28db01b719003149a0d616934e469b1b83c0237f` |
| Статус | ДЕЙСТВУЮЩИЙ; LEGAL-001 TECHNICAL_ACCEPTED / LEGAL_PENDING; real-data AI CLOSED |

## 1. Активные документы

| Документ | Версия | Область |
|---|---|---|
| PLAN_CURRENT | 1.6.5 | Полный план с сохранённой историей |
| PROJECT_PASSPORT | 2.80 | Полный паспорт с сохранённой историей |
| SOURCE_AUDIT / CANONICAL_DOCUMENTS | 1.6.5 | Источники, evidence boundary, реестр |
| ROADMAP | 1.6.5 | Очередь после технической приёмки LEGAL-001 |
| NEXT_PACKAGE_PREPARATION | 1.6 | Owner/legal decisions → policy activation → controlled real-data AI-005 test |
| AI005_ACCEPTANCE_SUMMARY | 1.0 | Приёмка только документной части r1 |
| AI005_IMPLEMENTATION / AI005_RUNBOOK / AI005_VERIFICATION_STATUS | 2.0 | Технический r2 и границы проверки |
| AI005_SCOPE / AI005_DELIVERY_GUIDE | 2.0 | Объём и порядок передачи |
| LEGAL001_SCOPE / IMPLEMENTATION / RUNBOOK / VERIFICATION_STATUS | 1.1 technical acceptance | Versioned consent, production QA, PostgreSQL T-05/T-06, legal activation boundary |

## 2. Финальная техническая evidence chain LEGAL-001

Accepted technical main: `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`; tree `2616a3b15df09f85bf7ae261e605356fb9f52f9d`. Main CI #324, Package preflight #11 и LEGAL-001 PostgreSQL verification #5 — SUCCESS. Production runtime QA выполнен на `28db01b719003149a0d616934e469b1b83c0237f`; GitHub compare до accepted main содержит только verification workflow/guard/tests и не меняет application runtime.

Production QA закрыл health/readiness, closed AI status, privacy cache headers/anonymous isolation, consent conflicts, responsive 1280/768/390/360, ZIP export и TXT export. Heartbeat fix не воспроизвёл прежний startup FileNotFoundError на двух наблюдавшихся стартах. T-05/T-06 закрыли ранее заблокированные disposable PostgreSQL сценарии.

Не закрыты и не выдумываются: natural 24h cleanup cycle, historical pre-migration production backup evidence, old baseline consent record ID.

## 3. Юридическая граница

Technical acceptance не переводит policy в ACTIVE. `DRAFT / NOT_ACTIVE`, `REAL_DATA_SUPPORTED=False`, real-data Alice CLOSED и paid provider calls=0 сохраняются. Operator/legal entity, jurisdiction, launch countries, audience/age, storage/processors/cross-border/final retention и финальные Terms/Privacy/AI-consent остаются PENDING.

Полный AI-005 остаётся IN_PROGRESS / LIVE_NOT_ACCEPTED. Следующий шаг — owner/legal facts и финальные документы, затем отдельная policy activation, controlled real-data test и quality acceptance. AI-006 не начинается раньше.

## 4. Форматы и история

Markdown остаётся текстовым первоисточником. DOCX/PDF являются синхронизированными представлениями и не создают новое evidence сами по себе. Исторические CI304, layout fix, heartbeat fix и прежние release snapshots сохраняются отдельными документами/evidence; они не переписываются задним числом.

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
