# HOST-001 — runbook Yandex Cloud Russia

| Поле | Значение |
|---|---|
| Версия | Stage C successor / 1.2 candidate |
| Дата | 6 октября 2026 |
| Статус | IMPLEMENTED_CANDIDATE / APPLY_FORBIDDEN_WITHOUT_OWNER_AUTHORIZATION |
| Accepted application schema | `20261002_0023` unchanged |
| Default DB topology | `single` PostgreSQL 18 host |
| Future DB topology | `two` private hosts in distinct Russia zones |

This runbook supersedes only the operational candidate instructions. Historical HOST-001 evidence remains historical.

## 1. Preflight

Confirm the exact GitHub branch/PR and current Yandex Cloud prices before any billable action. Never paste cloud tokens, PostgreSQL passwords, private SSH keys, Lockbox values, backup keys, presigned URLs or production DATABASE_URL into chat/GitHub.

Run offline validation first. Green CI proves repository preparation only; it is not proof that resources exist, backups restore, localization requirements are met, or production is safe.

## 2. Stage B topology boundary

The owner-approved launch profile is one application VM plus one private Managed PostgreSQL 18 host. Set `postgresql_host_profile = "single"`. The retained `two` profile adds a second private host and requires a distinct Russia zone; enabling it requires a later owner cost/availability decision.

No schema migration is introduced by Stage B.

## 3. Controlled startup

Default/rehearsal startup must not implicitly execute migrations or background writers.

1. Load protected runtime values from Lockbox outside Terraform state.
2. Start only the components required for synthetic verification.
3. After the target database has been restored/created and explicitly approved for migration, run the migration service as an explicit one-off target. Do not use a broad `--profile migration up` command because unprofiled services would also start:

   ```bash
   python infra/yandex-cloud/run_with_lockbox.py -- \
     docker compose -f infra/yandex-cloud/compose.yaml run --rm --build migrate
   ```

4. After migration/restore verification, start only the normal web path:

   ```bash
   python infra/yandex-cloud/run_with_lockbox.py -- \
     docker compose -f infra/yandex-cloud/compose.yaml up -d --build web gateway
   ```

5. Enable writers only after database revision/data checks pass:

   ```bash
   python infra/yandex-cloud/run_with_lockbox.py -- \
     docker compose -f infra/yandex-cloud/compose.yaml --profile writers \
     up -d --build sync-worker privacy-worker
   ```

6. Keep AI fail-closed: `AI_ENABLED=0`, `AI_KILL_SWITCH=1`, `AI_SYNTHETIC_ACCESS_ENABLED=0`.

## 4. PostgreSQL 18 / TLS

Target database major version is 18; use PostgreSQL 18 `pg_dump`/`pg_restore` for migration and drills. The Yandex ops image is separate from the shared Render Dockerfile.

Backup/restore clients must use:
- `PGSSLMODE=verify-full`;
- `PGSSLROOTCERT=/etc/ssl/certs/yandex-cloud-ca.pem`;
- `PGTARGETSESSIONATTRS=read-write`.

The Yandex Lockbox launcher rejects `DATABASE_URL` unless it contains exactly `sslmode=verify-full`, `sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem` and `target_session_attrs=read-write`; a weaker URL therefore cannot override the ops environment. A wrong/untrusted CA must fail closed; the real TLS drill remains NOT_RUN until a disposable TLS PostgreSQL target exists.

## 5. Backup and off-VM copy

Create encrypted backups with the existing OPS tooling. A Docker volume on the VM is temporary staging only, not an independent backup.

The opt-in `backup-export` profile accepts only a backup whose manifest says `encrypted=true`, whose size/SHA-256 match, whose file has the `ACAOPS1` envelope, and whose AES-256-GCM tag authenticates with `BACKUP_ENCRYPTION_KEY` before upload. Backup and manifest presigned URLs must resolve to distinct HTTPS object targets even if their signature queries differ.

Stage C now has a reviewed provisioning path for the required temporary storage resources:
- `field_test_resources_enabled=true` creates a private, `force_destroy` Object Storage bucket capped at 1 GiB with a one-day lifecycle;
- the VM service account receives `storage.uploader`;
- a temporary service-account static key is written directly into a separate Lockbox secret through `output_to_lockbox`;
- the key values are never Terraform outputs.

For the Stage C path, load the application secret and then the backup-key secret before starting the exporter:

```bash
python infra/yandex-cloud/run_with_lockbox.py --secret-id "$YC_LOCKBOX_SECRET_ID" -- \
  python infra/yandex-cloud/run_with_lockbox.py --secret-id "$YC_BACKUP_LOCKBOX_SECRET_ID" -- \
  docker compose -f infra/yandex-cloud/compose.yaml --profile backup-export \
    run --rm backup-export
```

The exporter creates short-lived Yandex Object Storage PUT presigned URLs in process when externally supplied URLs are absent. Do not print or persist the generated URLs, static secret key or `BACKUP_ENCRYPTION_KEY`.

An actual independent restore drill into the Terraform-created disposable PostgreSQL 18 target is required before production migration.

## 6. Proxy / client IP

Yandex Caddy removes any inbound `CF-Connecting-IP` and replaces `X-Forwarded-For` with the observed network peer before forwarding to the app. This keeps the current Render/Cloudflare application behavior intact while preventing direct Yandex clients from selecting the rate-limit identity via forged Cloudflare headers.

Verify this again during the field test with the actual ingress path.

## 7. Billable field test — separate approval required

Execution must follow `docs/HOST001_STAGE_C_OPERATOR_CHECKLIST_20261008.md`. The checklist fixes the exact order, stop conditions, synthetic-only runtime payload, backup/restore drill, evidence capture and recovery path for the approved Stage C window.


Only after owner approval:
1. start from `terraform.stage-c.tfvars.example`, keep `field_test_resources_enabled=true` and `foundation_deletion_protection=false`, and supply both PostgreSQL passwords through protected `TF_VAR_...` environment values;
2. configure Yandex authentication in a protected environment;
3. review the exact Terraform plan, SKU/cost, Russia zones, temporary bucket/static-key Lockbox path and disposable restore cluster;
4. apply only the approved plan;
5. populate the application Lockbox secret outside Terraform; the field-test Object Storage key payload is created directly in its separate Lockbox secret by the provider;
6. perform synthetic health/TLS and wrong-CA tests;
7. create the encrypted backup, export it off-VM and restore into the isolated Terraform-created PostgreSQL 18 target;
8. record measured duration/results and execute the reviewed teardown before the approved window expires.

If **no continuation** is approved, destroy the entire field-test foundation while `foundation_deletion_protection=false`; this is why Stage C preconditions reject protected creation.

If the owner separately approves retaining the foundation, first apply a reviewed plan with `field_test_resources_enabled=false` and `foundation_deletion_protection=true`. That removes the temporary bucket/key/restore cluster and turns protection back on for retained persistent resources.

No real-data Alice call is part of this field test.

## 8. Production migration — separate MIG-001 approval required

Before cutover freeze every old writer, take a final consistent encrypted dump using a direct/non-pooled Neon connection and PostgreSQL 18 client tools, restore to an empty target, verify schema `20261002_0023` and owned data, then run controlled target QA before opening writes.

After any new target writes, do not simply point traffic back to stale Neon. Preserve target changes and use a reviewed reverse-transfer/repair plan.

## 9. Domain / email

Until DOMAIN-001 the Caddy default remains controlled HTTP smoke only. Public traffic requires a commercial domain, TLS, PUBLIC_BASE_URL/TRUSTED_HOSTS, OAuth callback updates and verified transactional email.

## 10. Explicit prohibitions

Without later owner authorization: no Terraform apply, no production SQL/dump/restore, no cloud resource creation, no Render/Neon/Yandex production configuration changes, no paid Standard activation, no real-data AI, and no claim of LEGAL_PASS/COMPLETE.
