# HOST-001 / Issue #73 Stage C — synthetic field-test plan

| Поле | Значение |
|---|---|
| Дата | 6 октября 2026 |
| Статус | OWNER_AUTHORIZED / APPLY NOT_RUN / REVIEWED BOUNDED EXECUTION PATH |
| Baseline main | `5e34579b06b80df739ed0f625bce2901f71e1bbe` |
| Application schema | `20261002_0023` unchanged |
| Stage B | MERGED via PR #74; exact-head CI/review passed |
| Production migration | NOT_AUTHORIZED |
| Yandex billable resources | NOT_CREATED; owner-authorized Stage C apply pending execution |
| Real-data Alice | CLOSED |
| Legal policy | DRAFT / NOT_ACTIVE |

## 1. Purpose

Stage C prepares one short, synthetic, Russia-hosted field test for the Stage B infrastructure candidate. It is not MIG-001 and must not contain production/user data.

The repository now includes the **no-apply provisioning path** required to review that future test: temporary resources are absent by default and appear only with `field_test_resources_enabled=true`. The Stage C profile requires `foundation_deletion_protection=false` so the short test can be torn down inside its approved billing window.

Owner authorization recorded on 2026-10-07 permits only the bounded Stage C synthetic Terraform apply up to **1,000 RUB total / <=4 hours**. It does **not** authorize production SQL/dump/restore, Render/Neon configuration changes, MIG-001, domain cutover, email delivery, real-data Alice/Yandex AI calls, legal activation or payment activation.

## 2. Trudvsem decision

The current Trudvsem source is non-blocking for Stage C.

Production evidence after PR #74 showed repeated `opendata.trudvsem.ru` timeouts, but the same failure pattern existed before Stage B. One long timeout also caused PostgreSQL to terminate an idle transaction used by the advisory lock; the runtime supervisor restarted the worker and its heartbeat recovered.

Owner direction for this stage:

- do not spend implementation time fixing Trudvsem now;
- keep current behavior unchanged;
- during the future Russia-hosted synthetic field test, perform only a low-volume connectivity observation from the test VM;
- if the source remains unstable from Russia, removal/disablement is a separate source/package decision;
- do not make Stage C acceptance depend on Trudvsem success.

No claim is made that foreign hosting is the cause of the current failures. The Russia-hosted check is intended to test that hypothesis.

## 3. Read-only compatibility verification

Verified against current public Yandex Cloud documentation and the pinned Terraform provider documentation on 2026-10-06:

- Yandex Managed Service for PostgreSQL supports PostgreSQL 18.
- A one-host PostgreSQL cluster is supported with `network-ssd`; the official example uses 20 GB.
- Host class `s3-c2-m8` is documented as 2×100% vCPU / 8 GB RAM.
- `ru-central1-d` is documented as the recommended zone for new projects.
- Yandex documents PostgreSQL clusters with two or more hosts as automatically highly available. The initial single-host profile intentionally remains non-HA.
- Repository pin `yandex-cloud/yandex = 0.229.0` documents PostgreSQL `18` as an allowed `yandex_mdb_postgresql_cluster.config.version`.

Execution evidence through 2026-10-08: account quota checks PASS for Compute, Managed Databases and VPC/public IP; the remote-backend credentialed plan PASS on main `5baea91da5fc7a121312a82f3e55d677a9d269cb` (plan-only run #6); bounded apply runs #1 and #2 both stopped at the fresh-plan gate before teardown dispatch or Terraform apply, so no Stage C Terraform-managed billable resources were created. PR #84 added sanitized diagnostics to the bounded-apply plan gate. Live synthetic infrastructure creation and field-test evidence remain NOT_RUN.

Official references:

- https://yandex.cloud/ru/docs/managed-postgresql/
- https://yandex.cloud/ru/docs/managed-postgresql/operations/cluster-create
- https://yandex.cloud/ru/docs/managed-postgresql/concepts/instance-types
- https://yandex.cloud/ru/docs/managed-postgresql/concepts/
- https://yandex.cloud/ru/docs/overview/concepts/geo-scope
- https://github.com/yandex-cloud/terraform-provider-yandex/blob/v0.229.0/docs/resources/mdb_postgresql_cluster.md

## 4. Proposed field-test resources

Persistent launch candidate represented by Stage B:

- one Yandex VPC network;
- app subnet in `ru-central1-d`;
- DB subnet/private access path;
- security groups: public gateway 80/443, owner-approved SSH CIDR, PostgreSQL 6432 only from app security group;
- one non-preemptible VM: `standard-v3`, 2 vCPU at 100%, 4 GB RAM, 40 GB `network-ssd`, Ubuntu 24.04;
- one active/reserved public IPv4 for the app VM;
- one private Managed PostgreSQL 18 cluster, profile `single`, one `s3-c2-m8` host, 20 GB `network-ssd`;
- Yandex Lockbox secrets;
- private Object Storage STANDARD bucket for encrypted backup artifacts.

Temporary Stage C resources are now part of the reviewed Terraform path and remain disabled by default:

- one private Object Storage STANDARD bucket with `max_size=1 GiB`, `force_destroy=true` and one-day synthetic-object lifecycle;
- one `storage.uploader` grant for the VM service account;
- one temporary service-account static access key written directly to a **separate** Lockbox secret through provider `output_to_lockbox`; the secret value is not a Terraform output;
- one second private, disposable single-host PostgreSQL 18 cluster using `field_test_restore_resource_preset_id` (default `s3-c2-m8`) and 20 GB `network-ssd`;
- one synthetic restore user/database with a write-only password supplied only through `TF_VAR_field_test_restore_password`.

The exact non-secret profile is documented in `terraform.stage-c.tfvars.example`. If account quota or exact price makes the reviewed resources inappropriate, stop and return for owner approval instead of silently changing topology.

A control-plane prerequisite is intentionally outside the Terraform-managed resource graph: one dedicated private Object Storage bucket for remote Terraform state plus one static access key for the dedicated Stage C Terraform service account. The bucket stores only the Stage C state object (and any provider lock object), must have restricted access, and is removed manually after verified teardown and evidence capture. It is not application backup storage.

No load balancer, second app VM, replica DB host, Data Transfer, logical replication, public DB IP, production domain or production email provider is part of this field test.

## 5. Cost model and approval gate

Yandex pricing pages use 720 hours for monthly examples. Published components verified on 2026-10-06:

| Component | Calculation | Monthly planning amount |
|---|---:|---:|
| VM compute, 2×100% vCPU + 4 GB RAM | 720 × (2×1.24 + 4×0.33) | 2,736.00 RUB |
| PostgreSQL `s3-c2-m8` compute | 720 × (2×1.8792 + 8×0.5072) | 5,627.52 RUB |
| Active public IPv4 | 720 × 0.26352 | 189.73 RUB |
| Object Storage STANDARD, assumed 50 GiB | first 1 GiB free; 49×2.376 | 116.42 RUB |
| Lockbox planning assumption | 5 total secret versions + 10k gets | 102.43 RUB |
| **Verified subtotal** | excludes disks and several launch services | **8,772.11 RUB** |

Not yet priced to an account-confirmed final quote: VM `network-ssd`, PostgreSQL `network-ssd`, logs/metrics, transactional email, domain, billable traffic and any temporary restore cluster overhead.

The recurring owner budget remains **10,000–15,000 RUB/month excluding AI/provider usage**. Before any apply:

1. obtain the actual account/console quote for the exact Terraform SKU;
2. require the projected recurring launch total to remain <=15,000 RUB/month;
3. if the quote exceeds 15,000 RUB/month, stop and revise the design with the owner;
4. do not treat a billing alert as a technical hard cap.

Owner authorization update (2026-10-07): the Stage C field-test ceiling is **1,000 RUB total**, doubled from the earlier 500 RUB planning recommendation. This is an owner-approval ceiling, not an automatic Yandex spending limiter. Before or during apply, if the account-specific estimate can exceed 1,000 RUB, stop and request a new approval.

Target test window: up to 4 hours of primary resources, with the disposable restore cluster kept only as long as needed for the restore test. If the test cannot be completed within the approved window, stop rather than silently extending billable runtime.

The automated execution path is intentionally tighter than the owner ceiling: the apply workflow allows a 15–90 minute synthetic hold (default 60). The automatic recovery workflow caps the hold against an absolute destroy-start deadline 150 minutes after the source apply run begins. Automatic destroy planning is source-time-bounded, and the provider destroy apply is forcibly stopped no later than +225 minutes, leaving a 15-minute owner-boundary reserve inside the <=4 hour resource-lifetime ceiling. If that automatic path has already exhausted its source-derived deadline while billable resources remain, explicit manual recovery is still allowed: it skips the expired automatic deadline and instead gets its own immediate bounded cleanup window (20 minutes to obtain the reviewed destroy plan and at most 90 minutes from manual-recovery start for provider deletion). This exception exists only to minimize further spend and cannot authorize continued testing.

Pricing references:

- https://yandex.cloud/ru/docs/compute/pricing
- https://yandex.cloud/ru/docs/managed-postgresql/pricing
- https://yandex.cloud/ru/docs/vpc/pricing
- https://yandex.cloud/ru/docs/storage/pricing
- https://yandex.cloud/ru/docs/lockbox/pricing

## 6. Preconditions before a future apply

The live execution order is frozen in `docs/HOST001_STAGE_C_OPERATOR_CHECKLIST_20261008.md`. Do not improvise alternate startup, backup/restore or teardown steps during the billed window.


All conditions below are required:

1. explicit owner approval for Stage C billable field test and the approved spend ceiling;
2. active Yandex Cloud billing account and selected Russia region/folder;
3. account quota/availability check for VM, public IP and Managed PostgreSQL 18/`s3-c2-m8`;
4. exact Terraform plan reviewed against the approved resource list;
5. actual monthly launch quote <=15,000 RUB and field-test estimate within the approved test ceiling;
6. owner-approved `admin_cidr`;
7. protected Yandex credentials available outside Git/GitHub/chat;
8. synthetic-only database/backup payload prepared;
9. Stage C variables explicitly use `field_test_resources_enabled=true` and `foundation_deletion_protection=false`; a Terraform precondition rejects the temporary field-test profile if deletion protection would block teardown;
10. both PostgreSQL passwords are supplied through protected environment variables rather than tfvars/Git;
11. `REAL_DATA_SUPPORTED=False` and legal DRAFT unchanged;
12. rollback/teardown commands reviewed before creation;
13. a dedicated private Yandex Object Storage bucket exists for Terraform remote state, with restricted access and no production/user data; the owner-created bucket is outside the Stage C Terraform-managed resource graph and is included in the 1,000 RUB field-test ceiling;
14. protected `YC_STAGE_C_TFSTATE_BUCKET`, `YC_STAGE_C_TFSTATE_ACCESS_KEY` and `YC_STAGE_C_TFSTATE_SECRET_KEY` values are present in the `stage-c-yandex` GitHub Environment; the static access key belongs to the dedicated Stage C Terraform service account;
15. the apply workflow initializes that remote backend with S3 lockfile state locking, scans every Stage C Terraform state object in the dedicated bucket and refuses a new apply while any prior state still owns managed resources, then dispatches the separate teardown workflow **before** the billable Terraform apply begins. Recovery concurrency is keyed by the validated source apply run ID, so an unrelated older recovery cannot occupy the same GitHub concurrency group and cause the new lifecycle's pending teardown to be replaced. The durable state scan is the lifecycle-overlap gate; Terraform state locking remains the provider-operation serialization boundary. Cancellation during apply therefore leaves both recoverable remote state and an independent recovery path.

Execution principal for the bounded apply: use the dedicated Stage C service account only in the selected folder. During apply/teardown it must have the temporary folder-scoped `editor` role for resource lifecycle plus `resource-manager.admin` for the reviewed IAM bindings. Do not grant cloud-wide `admin`. Revoke these write roles after teardown (or reduce the account back to read-only access).

## 7. Field-test sequence

### 7.1 Provisioning boundary

- Copy the non-secret Stage C profile from `terraform.stage-c.tfvars.example`.
- Supply `TF_VAR_postgresql_app_password` and `TF_VAR_field_test_restore_password` only through a protected local environment.
- Run a credentialed `terraform plan` first.
- Confirm that the plan contains the single-host foundation **plus** only these Stage C extras: private bounded backup bucket, `storage.uploader` binding, separate Lockbox/static key, and one private disposable PG18 restore cluster/user/database.
- Confirm `foundation_deletion_protection=false` in the field-test plan. If deletion protection remains enabled, the repository precondition must stop the plan/apply.
- Do not continue if the plan proposes a second permanent DB host, public DB IP, unexpected IAM grants or unrelated resources.
- Apply only after the owner approves the exact plan/cost. That owner approval was recorded on 2026-10-07 with a 1,000 RUB total ceiling and <=4 hour boundary.
- Initialize the dedicated Yandex Object Storage S3 backend before the fresh plan. Each new apply run owns a distinct state object `host001/stage-c-<apply_run_id>.tfstate`; the apply derives it from `GITHUB_RUN_ID`, and recovery derives the exact same key from the validated `source_run_id`. Before planning, the apply scans the dedicated bucket for every `host001/stage-c*.tfstate` object and fails closed if any state still contains managed resources, preventing a second billable lifecycle while an earlier one remains live or partially created. Source revisions that still use the old shared `host001/stage-c.tfstate` layout are rejected by automated recovery because the shared object contains no durable source-run ownership proof. This is acceptable for this rollout because no billable Stage C apply workflow_dispatch run was executed before the per-run state design. The bucket name/credentials come only from protected GitHub Environment secrets.
- Dispatch the separate recovery-teardown workflow after the fresh create-only plan passes but **before** Terraform apply begins. Teardown concurrency is namespaced by `source_run_id`, so recovery for one lifecycle cannot replace the pending recovery for another lifecycle. Before checkout or protected credentials are used, teardown validates that `source_run_id` is the reviewed Stage C apply workflow on `main`, accepts either the bare or ref-qualified workflow path, and requires `head_sha` to match `source_sha`. Monitoring requests have explicit connection/transfer deadlines and retry transient GitHub API failures. After a successful apply it waits only within the bounded synthetic field window and absolute teardown reserve; after failure/cancellation it skips the window and tears down tracked resources immediately. If a hard-cancelled apply leaves the S3 state lock behind, teardown may perform exactly one guarded `terraform force-unlock` only after the exact source apply run is confirmed terminal **and** a fresh GitHub Actions query proves that no other Stage C apply run is active or queued, then re-plan the reviewed destroy.

### 7.2 Controlled startup

- Load secrets from Lockbox outside Terraform state.
- Default/rehearsal startup must not run schema migration, Trudvsem sync or privacy cleanup automatically.
- Run the migration service only as the explicit one-off target documented in HOST001_RUNBOOK.
- Keep AI fail-closed.

### 7.3 PostgreSQL 18 / TLS

With synthetic data only:

- confirm actual server major version 18;
- verify successful `verify-full` connection using the Yandex CA;
- verify a deliberately wrong/untrusted CA fails closed;
- verify `target_session_attrs=read-write` reaches the writable host;
- confirm schema stays `20261002_0023`.

### 7.4 Encrypted backup and restore

- create a logical PostgreSQL 18 backup using the Yandex-specific PG18 ops image;
- encrypt it and verify manifest size/SHA-256/authentication;
- load the normal runtime Lockbox secret and the separate Stage C Object Storage Lockbox secret in sequence;
- let the exporter generate short-lived Yandex Object Storage PUT presigned URLs in process when external URLs are not supplied; do not print or persist the URLs/keys;
- export backup + manifest to the Terraform-created private Object Storage bucket;
- verify the off-VM objects exist;
- restore into the disposable isolated PostgreSQL 18 target;
- verify schema revision, representative synthetic owner/JOB/legal structures, indexes/constraints/sequences and resume-asset bytes;
- delete the disposable restore target after evidence capture.

No production rows, credentials, OAuth tokens or personal data may enter the field test.

### 7.5 Proxy/client-IP test

Against the test VM/gateway:

- send requests with forged `CF-Connecting-IP` and `X-Forwarded-For`;
- confirm Caddy strips/rebuilds the trusted client identity as designed;
- confirm the rate-limit identity cannot be selected by the client-supplied Cloudflare header.

### 7.6 Trudvsem location observation

This is diagnostic only and cannot block Stage C.

If the owner-approved field test is already running:

- issue at most three low-volume public API requests from the Russia VM with no user data;
- record only status/latency/error type, not response payload;
- compare with the repeated Render/Oregon timeout pattern;
- do not modify production Trudvsem state from this test.

Outcomes:
- stable from Russia: keep source provisionally and reassess after migration;
- still unstable: open a separate source-disable/removal decision;
- ambiguous: leave source unchanged.

### 7.7 Teardown

The Stage C profile is intentionally created with `foundation_deletion_protection=false`. This prevents the current Stage B deletion-protection defaults from trapping billable test resources beyond the approved window.

Before the approved field-test window expires choose exactly one reviewed outcome:

**A. No continuation approved (default field-test outcome)**

- stop test services;
- keep `field_test_resources_enabled=true` and `foundation_deletion_protection=false`;
- recover the encrypted Terraform state from the apply run;
- run and review `terraform plan -destroy`;
- apply that reviewed destroy plan in the dedicated teardown workflow;
- verify the app VM, public IP, both PostgreSQL clusters, temporary static key/Lockbox secret and backup bucket are gone;
- verify no unexpected billable resource remains.

**B. Foundation continuation separately approved**

- set `field_test_resources_enabled=false`;
- set `foundation_deletion_protection=true`;
- review/apply that exact plan; it removes the temporary restore cluster, bucket and static access key while re-enabling protection on the retained foundation;
- verify no temporary field-test resource remains.

Do not improvise a third path or silently extend the test window. Production Render/Neon remains untouched by Stage C.

Cancellation/recovery rule for the automated path: the dedicated Yandex Object Storage backend is initialized with `use_lockfile=true` before apply and the separate teardown workflow is dispatched before apply. Teardown concurrency is namespaced by the validated source apply run ID, preventing an unrelated older recovery from replacing the pending recovery for the current lifecycle; a durable pre-apply scan refuses any new lifecycle while an older Stage C state still owns managed resources. Terraform's remote state lock serializes provider operations. Before any guarded stale-lock removal, recovery proves the exact source run is terminal and queries the apply workflow to confirm that no other Stage C apply run is active or queued. The automatic recovery job validates the exact source run before checkout, bounds every GitHub API request, and enforces source-derived destroy deadlines: plan work must begin within the reserved window and provider deletion is bounded to end attempts by +225 minutes from source apply start. The apply summary records the exact commit and apply run ID. If the automatic teardown workflow is cancelled, times out or otherwise fails, rerun `HOST-001 Stage C recovery teardown` from `main` with acknowledgement `DESTROY_STAGE_C_SYNTHETIC_1000_RUB`, the recorded apply commit/run ID and `hold_minutes=0`. For manual recovery, the 90-minute recovery clock is recorded immediately when the recovery request is admitted, before checkout/provider/backend setup; Terraform init/validate and destroy planning must fit inside that fixed window. Manual recovery still requires the exact source run to be completed and the same no-other-active-apply proof for guarded stale-lock removal, but it remains usable after the automatic +170/+225 minute deadlines have expired. Recovery opens only `host001/stage-c-<source_run_id>.tfstate`; legacy shared-key source revisions are rejected because the fixed object has no source-run ownership proof. It then reviews a delete-only allowlisted destroy plan and applies only that plan.

## 8. Acceptance evidence for Stage C field test

A future Stage C execution can be marked PASS only with evidence for:

- reviewed exact Terraform plan and resource list;
- actual field-test cost/estimate within owner-approved ceiling;
- PostgreSQL 18 running on the created managed host;
- strict TLS success + wrong-CA failure;
- read-write target selection;
- controlled startup with no unintended writers;
- encrypted backup exported off-VM and authenticated;
- isolated PG18 restore successful;
- proxy spoofing test blocked;
- remote Terraform state remained recoverable through apply/teardown and the dedicated backend bucket/static key were removed after evidence capture;
- teardown verified;
- no production data/config change;
- Alice/Yandex AI calls 0;
- email/employer sends 0.

Trudvsem outcome is recorded separately and does not determine Stage C PASS.

## 9. Stop conditions

Stop before or during apply if any of the following occurs:

- projected recurring launch cost >15,000 RUB/month;
- projected field-test spend can exceed the approved ceiling;
- PostgreSQL 18 or the selected host class is unavailable in the account;
- Terraform plan contains resources outside the reviewed scope;
- any connection points to production Neon or another production data source;
- real user data appears in the test payload;
- wrong-CA connection succeeds;
- DB is assigned a public IP unexpectedly;
- default/rehearsal startup launches external writers;
- secrets appear in plan/logs/GitHub/chat.

## 10. Explicit NOT_RUN after this planning PR

Current execution status:

- Yandex quota/account check: PASS on 2026-10-07 for the reviewed Compute, Managed Databases and VPC/public-IP requirements;
- credentialed Terraform plan: PASS on main `085c6f4f44083427b3e8ab6ed37e646061a076a6` via bounded plan-only workflow run #4;
- Terraform apply/resource creation: OWNER_AUTHORIZED on 2026-10-07 up to 1,000 RUB total / <=4 hours; NOT_RUN until the bounded apply workflow is reviewed and dispatched;
- synthetic PG18 field test: NOT_RUN;
- off-VM real Object Storage upload: NOT_RUN;
- isolated managed PG18 restore: NOT_RUN;
- Trudvsem Russia-VM observation: NOT_RUN;
- DOMAIN-001: NOT_RUN;
- MIG-001 production cutover: NOT_AUTHORIZED;
- production SQL/dump/restore: NOT_RUN;
- legal activation: NOT_RUN;
- real-data Alice: CLOSED.

This planning document does not make INFRA/HOST/OPS/MIG COMPLETE.
