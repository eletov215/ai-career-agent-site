# HOST-001 — verification status

| Поле | Статус |
|---|---|
| Package | HOST-001 / Issue #73 infrastructure track |
| Baseline main | `5e34579b06b80df739ed0f625bce2901f71e1bbe` |
| Application schema | `20261002_0023` unchanged |
| Launch DB profile | single private PostgreSQL 18 |
| Future DB profile | two private PostgreSQL 18 hosts / separate approval |
| Stage B implementation | MERGED / PR #74 |
| Stage B reviewed head | `7302469da3aeb77c552e04e34fc67350200b2b78` |
| GitHub exact-head CI | PASS — CI #508, HOST-001 #57, Package preflight #101, JOB-002 #28, JOB-003 #25, JOB-004 #20, AI-005 synthetic #82 |
| Final Codex review | PASS — no major issues on reviewed head |
| Terraform fmt/init/validate | PASS in HOST-001 exact-head GitHub Actions |
| Package/unit guards | PASS in exact-head GitHub Actions |
| Current Render auto-deploy | LIVE — `dep-db2ckc67bikc73drkajg` on merge commit `5e34579b...` |
| Post-merge Render smoke | PASS_WITH_NONBLOCKING_TRUDVSEM_WARNING |
| Yandex infrastructure deployed | NO |
| Yandex billable actions | 0 |
| Production DB migration | NOT_RUN / NOT_AUTHORIZED |
| Disposable PG18 restore/TLS drill | NOT_RUN |
| Field network test | NOT_RUN |
| OPS-002 independent restore drill | NOT_RUN |
| Stage C implementation prep | PR #75 CANDIDATE — bounded opt-in Terraform/export path; no apply |
| Stage C billable field test | NOT_AUTHORIZED |
| DOMAIN-001 | PENDING |
| MIG-001 production cutover | NOT_AUTHORIZED |
| Legal activation | DRAFT / PENDING |
| Real-data Alice | CLOSED |
| Overall INFRA/HOST/OPS/MIG acceptance | NOT_COMPLETE |

## Stage B evidence

PR #74 implemented and merged the explicit single-host profile, PostgreSQL 18 Yandex ops tooling, controlled migration/writer profiles, Yandex proxy header hardening, encrypted off-VM backup export path and updated guards/runbook.

Before merge, exact-head GitHub Actions were green and the final Codex review reported no major issue. The merge did not authorize or perform Terraform apply, Yandex resource creation or production database migration.

Render auto-deployed the merge because the existing service tracks `main`. The observed runtime initialized successfully with schema `20261002_0023`; home checks returned HTTP 200, privacy cleanup completed, and no 500/502/503 were found in the checked post-deploy window. This is evidence for continued current-Render health, not evidence that Yandex HOST-001 was deployed.

## Trudvsem recorded limit

Repeated Trudvsem upstream timeouts are pre-existing and are not treated as a Stage B regression. During the latest observed failure, the long external wait also led to a PostgreSQL `IdleInTransactionSessionTimeout` when the advisory lock was released; the runtime supervisor restarted the worker and its heartbeat recovered.

Owner direction is to defer a Trudvsem code fix. A future Russia-hosted field test may make a low-volume connectivity observation to test whether hosting geography affects reliability. If instability remains, source removal/disablement is a separate decision. HOST-001 Stage C must not claim the geography hypothesis as proven.

## Stage C planning state

Read-only research confirms:

- Yandex Managed Service for PostgreSQL documents PostgreSQL 18 support;
- official documentation includes one-host `network-ssd` clusters and 20 GB examples;
- `s3-c2-m8` is documented as 2×100% vCPU / 8 GB RAM;
- `ru-central1-d` is recommended for new projects;
- pinned Terraform provider `0.229.0` documents PostgreSQL 18 as an allowed cluster version.

PR #75 now carries both the dated Stage C plan and a bounded no-apply implementation path for the resources Codex review identified as missing: an opt-in private Object Storage bucket/static key stored through separate Lockbox, and an opt-in disposable PG18 restore cluster. The default Terraform profile still creates none of those Stage C extras.

The Stage C profile also parameterizes foundation deletion protection. Field-test creation requires `foundation_deletion_protection=false`, while retained launch resources continue to default to protected mode. This prepares deterministic teardown without creating any Yandex resource in CI.

## Remaining evidence

A separately approved Stage C execution must verify account-specific quota/SKU availability, exact cost, created PG18/TLS behavior, proxy behavior, controlled startup, backup export and isolated restore, followed by teardown evidence. PR #75 CI/review must be re-established on its final head after these Stage C implementation changes.

Production cutover, domain/email readiness, legal activation and real-data AI remain separate later gates.

No offline test, GitHub CI result or current Render smoke is legal approval, localization proof, Yandex deployment evidence or authorization for production migration.
