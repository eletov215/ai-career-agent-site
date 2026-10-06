# AI Career Agent — package registry / current successor

| Поле | Значение |
|---|---|
| Successor release / date | 1.2 / 6 октября 2026 |
| Source canonical predecessor | ACA_PACKAGE_REGISTRY v1.1 FINAL / 2 октября 2026 |
| Current main | `cc12b7de80b73f372aa185fadc1e49f58e9c2817` |
| Production schema | `20261002_0023` |
| Package IDs | 46; no new package ID invented by this sync |
| JOB-004 | COMPLETE |
| DOC-001 | ONGOING |
| Real-data AI | CLOSED |
| Legal | LEGAL-001 TECHNICAL_ACCEPTED / LEGAL_PENDING |
| Yandex billable resources | 0 / NOT_CREATED |

## 1. Как читать текущие статусы

- **COMPLETE** — пакет принят только в зафиксированном scope.
- **ONGOING** — постоянный процесс.
- **IN_PROGRESS** — реализация/подготовка идёт, но пакет целиком не принят.
- **NEXT / NOT_RUN** — следующий проверочный gate; фактический прогон ещё не выполнен.
- **PLANNED** — пакет предусмотрен и остаётся в очереди.
- **DEFERRED** — сознательно отложен.
- **TECHNICAL_ACCEPTED / LEGAL_PENDING** — техническая часть принята, юридическая активация не завершена.

Граница AI неизменна: `REAL_DATA_SUPPORTED=False`, real-data Alice CLOSED, employer auto-send выключен, LEGAL_PASS не заявлен.

## 2. Все 46 package IDs

| ID | Приоритет | Текущий статус | Граница |
|---|---|---|---|
| FND-001 | P0 | COMPLETE | Базовые тесты и CI перед архитектурными изменениями. |
| FND-002 | P0 | COMPLETE | Конфигурация приложения и разделение development/test/production. |
| DATA-001 | P0 | COMPLETE | PostgreSQL и Alembic migrations вместо временной SQLite. |
| DATA-002 | P0 | COMPLETE | Базовая доменная модель и слой доступа к данным. |
| SEC-001 | P0 | COMPLETE | Базовое усиление безопасности и proxy-aware rate limiting. |
| OPS-001 | P0 | COMPLETE (tooling) | Observability/alerts/backup tooling; independent production restore remains OPS-002/REL work. |
| INFRA-PREP-001 | P0 | COMPLETE | Hosting-independent Docker/Compose/probes/CI baseline. |
| DOC-001 | P0 | ONGOING | Canonical/repository synchronization. Issue #76 is current successor sync. |
| SYNC-001 | P0 | COMPLETE | Trudvsem durable worker. Current instability is recorded separately and not rewritten into this historical acceptance. |
| SYNC-002 | P1 | COMPLETE | Incremental sync/checkpoint/retry/stale cleanup. |
| SEARCH-001 | P0 | COMPLETE | Unified vacancy schema and normalization. |
| SEARCH-002 | P0 | COMPLETE | Conservative cross-source deduplication preserving origins. |
| SEARCH-003 | P0 | COMPLETE | Stable pagination/sorting/counts. |
| SEARCH-004 | P1 | COMPLETE | Main `/vacancies` route and safe source states. |
| SEARCH-005 | P1 | COMPLETE | Source health/admin center. |
| AUTH-001 | P0 | COMPLETE (logic); production email gate PENDING | First-party account, verification/reset, revocable sessions. Gmail API acceptance was staging-only; see production email gate below. |
| AUTH-002 | P0 | COMPLETE | Owner-bound HH/SuperJob OAuth identities and connection management. |
| PROF-001 | P1 | COMPLETE | Structured career profile, versions, ownership, stale-write protection. |
| PROF-002 | P1 | COMPLETE | Text PDF import via proposal/review/explicit confirmation. |
| PROF-003 | P1 | COMPLETE | Server drafts, autosave, versions, assets, PDF export. |
| PRIV-001 | P1 | COMPLETE | Export/delete/retention worker/privacy audit. |
| AI-BENCH-001 | P0 | COMPLETE (synthetic) | Alice synthetic golden benchmark; not real-data admission. |
| AI-PROVIDER-001 | P0 | COMPLETE | Provider strategy/technical baseline; public real-data AI closed. |
| AI-001 | P1 | COMPLETE (synthetic) | Provider-neutral runtime, cost guards, limits, idempotency/manual fallback. |
| AI-002 | P1 | COMPLETE (synthetic/reference) | Resume analysis foundation. |
| AI-003 | P1 | COMPLETE (synthetic/reference) | Adaptive interview foundation. |
| AI-004 | P1 | COMPLETE (synthetic/reference) | Explainable vacancy-match foundation. |
| AI-005 | P1 | COMPLETE (controlled synthetic live) | Cover-letter pipeline accepted synthetically in production; real-data CLOSED. |
| AI-006 | P1 | COMPLETE (synthetic/offline) | Deterministic quality/hallucination gate. |
| JOB-001 | P1 | COMPLETE | Server-saved vacancies and owner isolation. |
| JOB-002 | P1 | COMPLETE | Internal tracker and immutable action history. |
| JOB-003 | P2 | COMPLETE (in-app only) | Voluntary in-app reminders; no external sends. |
| JOB-004 | P2 | COMPLETE | Personal request-time analytics; production SITE QA PASS; schema unchanged. |
| INFRA-001 | P0 | IN_PROGRESS | Russia-hosted field validation is now represented by Issue #73 Stage C; billable field test still NOT_RUN. |
| REED-COMPAT-001 | P0 | NEXT / NOT_RUN | Technical and contractual Reed API check using the selected Russia-hosted source IP. |
| HOST-001 | P0 | IN_PROGRESS | Stage B + Stage C provisioning path merged; no Yandex apply/resource creation. |
| OPS-002 | P0 at hosting | PLANNED / FIELD EVIDENCE PENDING | Real off-VM backup + isolated PG18 restore drill required before migration acceptance. |
| DOMAIN-001 | P0 before beta | PLANNED | Project domain, DNS/TLS, PUBLIC_BASE_URL/TRUSTED_HOSTS, callbacks; now explicitly coupled to production-email readiness. |
| MIG-001 | P0 | PLANNED / NOT_AUTHORIZED | Production PostgreSQL/application cutover with recovery/rollback. |
| PERF-001 | P2 | PLANNED | Frontend/static optimization. |
| A11Y-001 | P2 | PLANNED | Keyboard/screen reader/zoom/reduced-motion accessibility. |
| LEGAL-001 | P0 before public AI | TECHNICAL_ACCEPTED / LEGAL_PENDING | Technical consent/privacy baseline accepted; legal activation/requisites pending. |
| ANL-001 | P2 | PLANNED | Internal product analytics without resume/letter content. |
| BILL-001 | P3 | DEFERRED | Plans/payments/usage limits. |
| SRC-001 | P3 | PLANNED / OWNER-SELECTED PRE-RELEASE | New vacancy sources must remain explicit. Execute after migration evidence; Reed first only if REED-COMPAT-001 passes. |
| REL-001 | P0 for release | PLANNED | Final MVP 1.0 pre-release verification. |

## 3. Production email gate — no new package ID

This sync deliberately does not invent a 47th package.

`AUTH-001` remains COMPLETE for its accepted logic/security scope. A separate **P0 pre-release gate** records the missing production transport:

- project-owned sender/domain;
- production-grade transactional provider or owned mail infrastructure;
- SPF, DKIM and DMARC;
- bounce/complaint/reputation handling;
- successful real registration verification, resend, forgot-password and reset E2E;
- no sensitive recipient/token/provider-response data in logs.

Personal Gmail API is not accepted for beta/commercial delivery. Owner evidence on 2026-10-06 says current verification email is not arriving. The exact immediate cause is NOT_PROVEN by this documentation change.

## 4. Vacancy-source sequence

1. Stage C creates the temporary Russia-hosted field environment only after separate billable approval.
2. Run `REED-COMPAT-001` from the selected Russia source IP.
3. Observe Trudvsem from Russia with only bounded diagnostic requests; result is non-blocking for Stage C.
4. Complete DOMAIN/email and then MIG-001.
5. Run `SRC-001`: integrate sources that passed technical/contractual review. Reed is first candidate if compatible; no other source is implicitly approved.
6. If Trudvsem remains unstable from Russia, open a separate disable/removal decision instead of treating it as a migration blocker.

## 5. Evidence boundary

This registry records accepted project state and owner sequencing only. It does not claim:

- Yandex resources created;
- a credentialed Terraform plan/apply;
- production email delivery fixed;
- Reed authenticated API success;
- Trudvsem geography cause proven;
- production migration;
- legal activation;
- real-data Alice.

Historical package evidence and dated canonical releases remain unchanged.
