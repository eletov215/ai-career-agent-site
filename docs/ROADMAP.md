# AI Career Agent — дорожная карта

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
| Версия / дата | 1.6.5 / 24 сентября 2026 |
| Актуальный пакет | AI-005 IN_PROGRESS; LEGAL-001 TECHNICAL_ACCEPTED / LEGAL_PENDING; LIVE_NOT_ACCEPTED |

## 1. Текущий результат

JOB-001 остаётся выполненным. Документная часть AI-005 r1 принята в зафиксированном объёме, r2 technical runtime сохранён закрытым для real-data. LEGAL-001 технически принят: consent/admission/privacy foundation, production QA и отдельные PostgreSQL T-05/T-06 verification gates прошли. Это не юридическая активация и не финальная приёмка AI-005.

## 2. Согласованная очередь

1. Владелец определяет юридические исходные данные: operator/legal entity, jurisdiction, launch countries, audience/age, storage/backup regions, processors/subprocessors, cross-border route, retention and contact channel.
2. На этих фактах готовятся и отдельно ревьюятся финальные Terms, Privacy Policy и AI-consent text/version; production legal policy переводится из DRAFT в ACTIVE только отдельным code/review change.
3. После legal activation выполняется ограниченный контролируемый real-data AI-005 test без автоматической отправки работодателю.
4. Проводится human quality acceptance RU/EN, short/full, tone, factuality/numbers and vacancy fit; только затем AI-005 может быть закрыт.
5. AI-006 и последующие пакеты начинаются после фактического закрытия AI-005, не раньше.

## 3. Что остаётся закрытым

`REAL_DATA_SUPPORTED=False` и DRAFT policy продолжают блокировать real-data Alice. Техническое consent acceptance само по себе не даёт разрешение провайдеру. Свободные live AI-003/004, автоматическая отправка писем, tracker и коммерческие тарифы не активируются этой приёмкой.

## 4. Операционные ограничения

Естественный 24h privacy-cleanup cycle в production отдельно не наблюдался; historical production backup перед исходной migration не доказан; старый baseline consent ID не восстановим. Эти пункты сохраняются как recorded limits и не переписываются в PASS.

## Исторический снимок предыдущей версии / 17 сентября 2026

Следующий текст сохранён полностью как история; актуальный статус и очередность заданы выше.

# AI Career Agent - ROADMAP / 1.6.2

| Field | Value |
|---|---|
| Date | 2026-09-17 |
| Full package | AI-005 IN_PROGRESS |
| Delivery | r1 NEEDS_VERIFICATION; LIVE_NOT_ACCEPTED |
| Base / candidate schema | 0019 / 0020 |

## 1. Agreed sequence and current work

JOB-001 COMPLETE -> AI-005 IN_PROGRESS -> AI-006 -> JOB-002..004. The current local r1 is a general owned letter document workflow (manual/local templates), not completed live AI-005. It attaches real saved vacancies and immutable confirmed-profile snapshots, with review/version/compare/TXT/privacy and stale-write controls. No pinned demonstration replaces the planned feature.

## 2. Remaining AI-005 work

General-input runtime admission, persistent generation accounting/idempotency, failure recovery, consent/data-routing and model/language quality must still be implemented and reviewed. LEGAL-001 stays deferred. There is no public generation activation in this delivery. AI-006 is not started merely because manual letters work.

## 3. Verification and release

Local candidate0020 requires new ordinary CI with Flask/PostgreSQL and site acceptance. Real Neon recovery point must be confirmed before deployment/migration. Previous optional-account/device/legacy and recovery gaps stay recorded. No GitHub/Render write was performed.

## 4. Historical predecessor (unchanged dated source)

The following reflects the previous release. It does not override the active sections above.

# AI Career Agent - ROADMAP / 1.6.1

| Field | Value |
|---|---|
| Current accepted package | JOB-001 / ВЫПОЛНЕНО / COMPLETE |
| Accepted code | `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c` |
| Accepted schema | 20260917_0019 |
| Evidence | Main CI283 success and owner final acceptance |
| Next | AI-005 preparation; no new package code started |
| Public AI | Disabled / manual |

## 1. Accepted result

Ordinary verified-account saved vacancies now have durable owner-bound source snapshots, private revisioned notes, a searchable library, duplicate-save protection, explicit legacy recovery, export and confirmed deletion. The owner confirmed required browser blocks and final regressions. AI-003/004 retain their limited accepted reference scopes.

## 2. Approved order and next gate

JOB-001 COMPLETE -> AI-005 -> AI-006 -> JOB-002..004. The owner's previously approved ordering remains unchanged. JOB-001 is no longer a missing dependency for letters. AI-005 still requires fresh input/ownership/provenance and quality/real-data/consent design; its live activation is not ready merely because saved vacancies work. See NEXT_PACKAGE_PREPARATION.md.

## 3. Open verification and operational work

Manual second-account isolation NOT RUN; no second active account. Actual legacy transfer and second-device outcomes are not separately identified. Test-database CI coverage remains distinct. Real Neon recovery point and production restore are not evidenced. Email delivery and LEGAL-001 remain open. The pre-release VPS/domain/migration/recovery plan is unchanged.

## 4. Release and rollback

This final documentation and status-guard update has no runtime, workflow or schema change. It has not been published; new remote CI is not claimed. Revert of these files needs no database downgrade. Runtime rollback0019->0018 remains a controlled destructive operation, not a routine test.

## 5. Version history

1.6.1 / 2026-09-17: accepted JOB-001, CI283/owner evidence and explicit exclusions. 1.6.0: owner-approved sequence and r1.1 rebuilt candidate. Older AI-004 and foundation decisions remain in the full PLAN_CURRENT.
