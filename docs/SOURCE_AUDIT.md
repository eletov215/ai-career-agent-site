# AI Career Agent — аудит источников

| Поле | Значение |
|---|---|
| Версия / дата | 1.6.5 / 24 сентября 2026 |
| Код | technical acceptance main `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`, tree `2616a3b15df09f85bf7ae261e605356fb9f52f9d`; production runtime evidence `28db01b719003149a0d616934e469b1b83c0237f` |
| Статус | ДЕЙСТВУЮЩИЙ; LEGAL-001 TECHNICAL_ACCEPTED / LEGAL_PENDING; AI-005 IN_PROGRESS / LIVE_NOT_ACCEPTED |

## LEGAL-001 final technical audit / 24 сентября 2026

GitHub source of truth подтверждён на main `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`, tree `2616a3b15df09f85bf7ae261e605356fb9f52f9d`. Post-merge CI #324, Package preflight #11 и LEGAL-001 PostgreSQL verification #5 завершены SUCCESS. Dedicated PostgreSQL run использовал disposable PostgreSQL 17 и не использовал production/provider credentials. Paid provider calls=0.

T-05/T-06 имеют отдельное воспроизводимое evidence: 2 dedicated T-05 tests passed; migration tools и `tests/test_legal001_migration.py` passed; восемь PostgreSQL regression files прошли без SKIPPED. Backup/restore проверяет exact before/after consent rows в отдельной disposable DB, а destructive downgrade проверяется только на disposable copy.

Production QA относится к `28db01b719003149a0d616934e469b1b83c0237f`. Сравнение GitHub между `28db01b719003149a0d616934e469b1b83c0237f` и `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2` показывает ровно три verification-only path: `.github/workflows/legal001-postgresql.yml`, `scripts/check_legal001_package.py`, `tests/test_legal001_postgresql.py`. Application runtime не менялся.

Manual production evidence: readiness/live/status PASS, privacy headers no-store PASS, unauthenticated isolation PASS, consent stale/conflict behavior PASS, responsive 1280/768/390/360 PASS, privacy ZIP PASS, TXT export PASS. Consent QA остался withdrawn/cycle4/revision2. Worker heartbeat после исправления наблюдался на двух стартах без прежнего FileNotFoundError; естественный 86400-second periodic cycle не наблюдался.

Не подменяем отсутствующие доказательства: historical production backup до исходной migration не зафиксирован; старый baseline consent record ID не был сохранён; natural 24h cleanup cycle NOT_RUN. Юридические facts и финальные документы также не определены. Policy DRAFT/NOT_ACTIVE и real-data Alice CLOSED.

## LEGAL-001 source/verification audit / 22 сентября 2026

GitHub branch `legal001-consent-foundation` подтверждён как потомок baseline main `f5ce1f42836e3872854332324f2ebdd9c8934b36`. Candidate head `fe3a7e1b553ccc9ebb5b956efce3779287291c04`, tree `55f03c287a3132aa9a2a55b7429c24d35e2a1957`. GitHub CI #304 completed/success именно для этого head.

В #304 успешны общий Python job, migration metadata, PostgreSQL migrations/integration, AI-005 r2 source-bound no-paid-call gate, dedicated `Verify LEGAL-001 consent and admission controls`, backup/restore и финальный `Run tests`. Платные `AI-BENCH-001 Live Yandex` и `Alice Final` jobs skipped. До этого эквивалентный code head успел выполнить полный suite: 1103 passed; отмена #303 произошла уже после PASS из-за 25-minute job timeout, после чего timeout увеличен до 40 минут и #304 завершился SUCCESS.

Это доказательство `CI_PASS`, а не production acceptance. Render deploy/0021 production migration, /health/ready, Cloud Browser QA и реальный provider call не выполнялись. Paid provider calls: 0.

Юридический текст остаётся DRAFT. Не определённые владельцем operator/legal entity, jurisdiction, launch countries, audience/age, storage regions, processor/subprocessor, cross-border, final retention, Terms/Privacy/AI-consent wording не выдумывались. Real-data admission остаётся CLOSED.

## 1. Подтверждённая основа

Через подключённый GitHub повторно прочитаны main, объект коммита и дерево dbcadece7814336942ea80da0ce85707a695c428. Сохранившийся ACA_AI005_r1_FULL.zip содержит 655 файлов и даёт то же Git-дерево при пересчёте путей, байтов и режимов. Этот архив материализует текущий main, а не заменяет его старой версией. Более старый ai-career-agent-site-main-2.zip с ресурсными файлами macOS не использован как кодовая основа.

Источники проекта, доступные через поиск файлов в этом запуске, вернули только два скриншота. Полные канонические тексты взяты из проверенного снимка текущего main и сохранившихся архивов r1; не заявляется получение отсутствующего нового ZIP через поиск. PLAN 1.6.2 и PASSPORT 2.77 сохраняются как предыдущая редакция, новая актуальная редакция — 1.6.3 и 2.78.

## 2. Доказательства принятой части

GitHub run35319097205, CI №285, attempt2, completed/success; Python job105527233222, dedicated AI-005 и общий Run tests успешны. Live Yandex/Alice задания skipped. Точное число тестов успешной попытки не извлекалось: число из неуспешного предыдущего запуска не переносится. Журналы и проверки старых пакетов остаются историческими.

Владелец подтвердил развёртывание0020, создание ручного письма, версии/сравнение/TXT, конфликт редактирования, экспорт/удаление, связи с вакансией, финальную регрессию, доступ после выхода и просмотр логов. Это PASS_OWNER_REPORTED, а не браузерный тест ассистента. Скриншот сравнения не является доказательством содержимого TXT; последнее основано на словах владельца.

Пустой профиль не позволил проверить предложения и изменение их источника. Второй аккаунт отсутствует. Устаревшее удаление не подтверждено отдельным сценарием. Реальная резервная копия Neon и восстановление рабочей базы не подтверждены.

## 3. Новый r2 и граница доверия

r2 имеет отдельный исходный SHA, реестр изменений и новые тесты. Новый контракт cover-letter-draft-v1 не унаследовал квалификацию grounded-v2.6.1 или AI-BENCH-001: эти старые контракты сохранены. Механические проверки цитат, чисел, формата и нескольких семейств утверждений не являются доказательством полной смысловой достоверности. Живой прогон нового контракта NOT RUN.

Существующие provider.py, settings.py, domain/ai.py, политики/тарифный снимок, evals, старые prompts/schemas, зависимости и render.yaml не изменены. В общий ledger добавлены версия контракта и транзакционное сохранение предложения. Новая миграция не нужна. Форма технического подтверждения не объявлена юридическим согласием.

## 4. Внешняя техническая сверка

20 сентября проверены официальные страницы Yandex AI Studio: API Chat Completions и отключение логирования. API описывает POST /v1/chat/completions, JSON Schema и зависимость поддерживаемых параметров от модели. Заголовок x-data-logging-enabled:false сохранён в существующем адаптере; это не новое свидетельство фактической настройки аккаунта и не обещание отсутствия любых служебных журналов. Даты/цены существующей политики не обновлялись без отдельного доказательства.

Источники: https://aistudio.yandex.ru/ru/docs/ai-studio/api/Chat-Completions/createChatCompletion ; https://aistudio.yandex.ru/ru/docs/ai-studio/operations/disable-logging . Сверка документации не заменяет настоящий пробный ответ выбранной модели.

## 5. Публикация и дальнейшая проверка

r2 подготовлен локально. Новый CI, развёртывание r2, платный вызов и приёмка живого текста не выполнялись. Результаты новых локальных проверок хранятся отдельно в evidence/ai-005-r2; пропуски Flask/PostgreSQL не считаются успехом. Следующая удалённая проверка должна относиться к новому SHA после разрешённой публикации.

## Исторический снимок предыдущей версии / 17 сентября 2026

Следующий текст сохранён полностью как история; актуальный статус и очередность заданы выше.

# AI Career Agent - source audit / AI-005 / 1.6.2

| Field | Value |
|---|---|
| Date | 2026-09-17 |
| Actual GitHub main | c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c |
| Exact baseline tree | 6bb34aba4c05213a3d68f784e9d9b385c6d577d3; 608 files |
| Authoritative uploaded docs | JOB-001 canonical ZIP1.6.1 / PASSPORT2.76 |
| New delivery | AI-005 r1 document workflow NEEDS_VERIFICATION; full feature IN_PROGRESS |
| Accepted / candidate schema | 20260917_0019 / 20260917_0020 |
| Remote write / candidate CI | Not performed / NOT RUN |

## 1. Source precedence and exact materialization

Main and its commit/tree were read through the connected GitHub. The retained JOB-001 REBUILT FULL archive was independently rehashed with Git blob/tree serialization; all608 files exactly match the current remote tree. The retained closure FULL adds only the unpublished21-file final docs/guard delta. All ten Markdown documents in the latest user canonical ZIP match closure sources. Older standalone AI-004 PDFs are historical, not the active plan. Resource-fork __MACOSX files are not project source and are excluded.

## 2. Changes and acceptance boundaries

The candidate adds general owner-bound letter documents, explicit reviewed versions, local selected-excerpt templates, stale conflicts, comparison/delete/TXT and privacy. Eleven existing runtime files are changed through an exact additive checksum chain. Existing provider policy, AI runtime, benchmark/prompts/schemas, config, dependencies, render settings and legal deferral stay byte-preserved. Historical exact-head tests move only their current-head assertions; old migrations still test their original target. New migration0020 adds three letter tables. Full AI-005 is not narrowed or claimed complete: general real-input provider integration remains unimplemented, not merely disabled.

## 3. Measured evidence and limits

The final available local full suite passed857 tests with27 skips and86 separately counted subtests (single run). Focused AI005 plus inherited package guards passed166 with2 skips. Flask HTTP modules and disposable PostgreSQL remain explicitly skipped locally; pinned installation was attempted and no package source was available. Forty actual-base-template offline Chromium layouts passed without horizontal overflow; external requests were blocked. This is not Flask E2E, CI, real-account testing, or model writing-quality evidence. New measurements and commands are in evidence/ai-005/local_verification.json. Base CI283 success is not new-candidate CI evidence.

## 4. Remaining work and publication

No GitHub push/PR/merge, Render deploy, real database migration/backup, real-data model call or paid benchmark occurred. Mandatory recovery proof before future0020 deployment is still absent. LEGAL-001, delivery email, optional manual isolation/device/legacy evidence and production restore remain as recorded. Continue full AI005 runtime/accounting/consent/quality work; do not close it from this manual/local workflow.

## 5. Previous source audit (dated history)

# AI Career Agent - source audit / JOB-001 closure

| Field | Value |
|---|---|
| Version | 1.6.1 / 2026-09-17 |
| Accepted package | JOB-001 / ВЫПОЛНЕНО / COMPLETE; r1.1 REBUILT |
| Accepted main | `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c` |
| Accepted tree | `6bb34aba4c05213a3d68f784e9d9b385c6d577d3` |
| Source materialization | 608 files; locally recomputed Git tree equals the directly read remote tree |
| Main CI | #283 / run35219447896 / success; Python job105195697162 |
| Staging | 20260917_0019; user-confirmed |
| Closure publication | Not performed; new local artifacts only |

## 1. Source of truth and retained lineage

GitHub main and its commit were read directly again. The preserved ACA_JOB001_r1_1_REBUILT_FULL.zip was extracted and all608 blobs and directories were serialized using Git hashing. The resulting tree matches `6bb34aba4c05213a3d68f784e9d9b385c6d577d3` exactly; therefore the archive is a verified materialization of current main, not an assumed stale ZIP. The active Markdown version1.6.0 on main is newer than the uploaded AI-004 PDFs1.5.7. Their AI-004 acceptance remains historical; they do not override the approved JOB-001 sequence or current0019 state.

The original JOB-001 r1 bytes were unavailable during reconstruction. This acceptance is explicitly of r1.1 REBUILT, not proof of equality to the lost archive. The complete historical audit is retained below.

## 2. Evidence hierarchy and closure boundaries

CI283 is completed/success on the exact accepted commit. Direct latest job-step reads show successful JOB-001, previous guards, PostgreSQL, backup/restore, container and full-test steps; optional paid jobs are skipped. The owner's confirmations establish real-site behavior and final logs; no raw account data or production logs were gathered. Exact CI test totals were not extracted and are not inferred from step counts.

Manual two-account isolation is NOT RUN. Legacy import and second-device subcases lack distinct outcomes in the broad confirmations and remain NOT SEPARATELY CONFIRMED. Real backup/snapshot and recovery are not evidenced. This is functional JOB-001 acceptance, not completion of infrastructure or public AI gates.

## 3. Change and next action

The release updates canonical status/history, evidence and status guards; it does not change application logic, workflow, migration0019 or real user data. The generated delta manifest lists the exact files. Original r1.1 runtime boundary hashes are preserved. New local closure tests are separate from accepted CI283; a later publication needs its own ordinary CI. Nothing is committed remotely by this task.

Next: AI-005 design and implementation after a fresh main audit, retaining the complete declared letter scope and explicit live-data/quality/consent/legal gates. No automatic send, hidden provider activation or copied synthetic score is authorized.

## 4. Historical source audit / 1.6.0

The following dated text describes the original reconstructed candidate. Its then-current/pending statements do not override sections1-3 above.

# AI Career Agent - source audit / JOB-001 reconstruction

| Field | Value |
|---|---|
| Version | 1.6.0 / 2026-09-17 |
| Candidate | JOB-001 r1.1 REBUILT / NEEDS_VERIFICATION |
| Verified main | `d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4` |
| Git tree | `53d86b0ff72f5090f214c20979df493e6f1f0ee3` |
| Preserved baseline | 565 files; full Git-tree serialization matched the remote tree |
| Closure overlay | Preserved AI-004 FINAL1.5.7 documentation/status guards; no runtime change in that overlay |
| Prior JOB-001 r1 | Source/archive absent in this runtime and absent from current GitHub branches; equivalence NOT ESTABLISHED |
| Remote writes | None in this reconstruction |

## 1. Source and authority

The connected GitHub reader returned main and its commit/tree again. Branch listing returned main only. The preserved AI-004 r1 FULL bytes were materialized and all Git blobs/trees recomputed to the exact remote tree. The newer preserved AI-004 closure files provide the accepted canonical evidence, not a new application commit. The latest user explicitly approved JOB-001 before AI-005, then requested recovery of a missing ZIP rather than publication.

The lost JOB-001 artifact was not reconstructed from a retained checksum manifest. Its previously claimed file count, tests and layout are not reused as proof. This rebuilt implementation follows the agreed functional scope but can differ in bytes, file names, tests and technical decisions. Release r1.1 and plan MINOR1.6.0 distinguish it from the unavailable r1.

## 2. Change boundary

`evidence/job-001/change_boundary.json` pins the ten reviewed existing runtime files and fourteen new runtime files against the 565-file accepted baseline. Earlier AI001..004 checkers recognize only this explicit additive chain; their prior acceptance, prompt/provider hashes and negative guards remain active. Protected AI contracts, dependency versions, config.py and render.yaml remain byte-preserved. The ordinary workflow adds JOB-001 checks without enabling its optional paid Alice jobs.

## 3. Verification and remaining gaps

Read JOB001_VERIFICATION_STATUS.md for measurements obtained during this reconstruction. Old main CI281 establishes only the accepted AI-004 baseline, not these changes. New remote CI, PostgreSQL/Flask execution in the installed environment, real deployment0019 and owner acceptance remain NOT RUN. No active second account or real database backup is inferred. Public AI, LEGAL-001 and email delivery constraints remain unchanged.

## 4. Historical source audit / preserved 1.5.7

The following is the prior accepted AI-004 closure audit. Its current/next/publication labels refer to that historical release and do not override this rebuilt candidate.

# AI Career Agent - source audit / AI-004 closure

| Field | Value |
|---|---|
| Version | 1.5.7 / 2026-09-17 |
| Accepted application | d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4 |
| Accepted application tree | 53d86b0ff72f5090f214c20979df493e6f1f0ee3 |
| Verified local source files | 565; exact Git-tree match |
| Preserved r1 FULL SHA-256 | b6b82fc8a1aacdf7c13b2d8b09542796c75fca6c21164a4bb6b029ffa66464d3 |
| PR / candidate | #38 / 39229d887fe8fa8fa58bb80df7ff6e751d91f819 |
| External CI | #280 / 35149229406; #281 / 35151012823; success |
| Accepted staging schema | 20260916_0018; owner-confirmed |
| Current package | ВЫПОЛНЕНО in synthetic/reference-only scope |
| Release change | Documentation and evidence only; remote publication not claimed |

## 1. Source of truth and exact materialization

GitHub main and its Git commit were read again during closure. The preserved AI-004 r1 FULL archive was extracted and every local file rehashed using Git blob/tree serialization. All 565 files produced the exact remote tree `53d86b0ff72f5090f214c20979df493e6f1f0ee3`. It is therefore a materialization of the accepted application, not an assumed old ZIP. The earlier code delta was 31 modified and 38 new files; PR #38 was already merged before this documentation task.

The 1.5.7 PATCH must be applied only to this verified source or reviewed against any newer main. Its generated manifest identifies every changed documentation file. Runtime bytes, migration0018, model/provider policy, templates and workflows remain unchanged. Two status checkers and their two existing test files are synchronized with closure; source-integrity and safety checks are preserved. This release does not claim a new commit, PR, CI run or deployment for documentation.

## 2. Evidence hierarchy

GitHub CI evidence was obtained directly: main #281 job104979035501 reports 71 focused and 804 final full-suite tests, no skips. Owner browser confirmations establish readiness0018, private RU/EN functionality, persistence/privacy/regressions and final gate/log review. These two evidence sources remain distinct.

Manual two-account isolation is NOT RUN; the owner expressly confirmed no second active account. Automated route and service ownership checks passed. A raw manual POST replay, deliberate restart test, real backup/snapshot and production restore are not invented. The latter remain operational evidence gaps; see AI004_VERIFICATION_STATUS.md.

## 3. Open questions and preparation

LEGAL-001, email verification delivery and real-data/live feature integration remain open. AI-005 lists JOB-001 as a dependency while the old queue places JOB-001 later. This conflict is recorded explicitly in NEXT_PACKAGE_PREPARATION.md without changing package order or starting implementation. A future plan change must follow the existing versioning rule.

## 4. Historical candidate audit (verbatim content from 1.5.6)

The following describes the pre-acceptance candidate on 2026-09-16. Its pending/current/next statements do not override sections 1-3.

### Source audit / AI-004 candidate

| Поле | Значение |
|---|---|
| Version | 1.5.6 / 2026-09-16 |
| Source of code | GitHub eletov215/ai-career-agent-site, main |
| Verified commit | c683520058cc1f729c79ed49ac5c213811e4c9f3 |
| Verified tree | 6458daea23371dadfbbd49d830abcdde44df1293 |
| Baseline file count | 527 |
| Baseline CI | #276 / run 35132463421 / success |
| Candidate | AI-004 r1 - НУЖНА ПРОВЕРКА |
| Schema | owner-accepted0017; candidate0018 not deployed by this work |

### 1. Source precedence and reconstruction

The user authorized reading main through the connected GitHub tool. Its branch, tree, AI-003 verification document and CI jobs were read before implementation. The preserved r1.2 FULL bytes were independently rebuilt into a Git tree equal to the remote tree; therefore those bytes are a verified local materialization of this exact main, not an assumed outdated ZIP. The complete SHA-256 file inventory and source audit are in evidence/ai-004.

Main contained accepted AI-003 r1.2 runtime, but still pending-status documentation. The previously delivered final 1.5.5 documentation-only patch had not been uploaded. This delivery includes that synchronization together with AI-004. It does not change the user's already-given AI-003 acceptance. No fresh main commit, PR, deployment or candidate CI success is claimed.

### 2. Delta and preserved sources

AI-004 adds score/validation, reports/series, a private session gate and RU/EN review, migration0018 and privacy/backup/tests/docs. Seven previously existing runtime files have explicit checksum-chain permission; all original benchmark/prompt/schema/provider policy files and dependencies remain byte-preserved. New reference copies are manifest-pinned. No project-source deletion is intended. AI003 historical migration tests explicitly target0017 while the application head advances to0018. Details: AI004_CHANGESET.md.

### 3. Evidence and limits

CI #276 was obtained directly for the baseline, including all named green jobs/steps. Owner staging0017/AI003 behavior remains conversation evidence, not a new tool-based Render check. The exact deployment-time origin of the earlier 404 was not established; no claim of a proven Blueprint overwrite is made. The session-review hotfix and its owner acceptance are established.

New local command results are in AI004_VERIFICATION_STATUS.md and local_verification.json. New GitHub CI, installed HTTP/PostgreSQL, Render0018 and owner review remain pending. A separate fresh two-account manual proof is not invented.

### 4. Open work

LEGAL-001 operator/market/data-location/consent decisions remain deferred. Staging verification email delivery remains unresolved. Free-form live Alice interview and arbitrary real-resume/live-vacancy matching are not delivered by these reference foundations and require explicit future feature/activation acceptance. Public runtime must remain manual/unavailable.

## 5. Version history

- 1.5.7 / 2026-09-17: final source/CI/owner audit; manual and recovery limits explicit.
- 1.5.6 / 2026-09-16: verified GitHub baseline and candidate provenance.

## Closure version history

1.6.1 / 2026-09-17: functional JOB-001 accepted, main CI283 and owner evidence recorded; current application materialization608 files verified.
