# HOST-001 — runbook Yandex Cloud Russia

| Поле | Значение |
|---|---|
| Версия | Stage B successor / 1.1 candidate |
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

The opt-in `backup-export` profile accepts only a backup whose manifest says `encrypted=true`, whose size/SHA-256 match, whose file has the `ACAOPS1` envelope, and whose AES-256-GCM tag authenticates with `BACKUP_ENCRYPTION_KEY` before upload. Export-only filenames/URLs are validated inside the exporter so an inactive profile does not require ephemeral credentials during normal Compose parsing. Backup and manifest presigned URLs must resolve to two distinct HTTPS object targets even if their signature queries differ. URLs are credentials: keep them out of logs/issues and make them short-lived.

An actual independent restore drill into an isolated PostgreSQL 18 target is required before production migration.

## 6. Proxy / client IP

Yandex Caddy removes any inbound `CF-Connecting-IP` and replaces `X-Forwarded-For` with the observed network peer before forwarding to the app. This keeps the current Render/Cloudflare application behavior intact while preventing direct Yandex clients from selecting the rate-limit identity via forged Cloudflare headers.

Verify this again during the field test with the actual ingress path.

## 7. Billable field test — separate approval required

Only after owner approval:
1. configure Yandex authentication in a protected environment;
2. review exact Terraform plan, SKU/cost and Russia zones;
3. apply the approved resources;
4. populate Lockbox outside Terraform;
5. perform synthetic health/TLS tests;
6. create encrypted backup and export it off-VM;
7. restore into an isolated disposable PostgreSQL 18 target and record measured duration/results.

No real-data Alice call is part of this field test.

## 8. Production migration — separate MIG-001 approval required

Before cutover freeze every old writer, take a final consistent encrypted dump using a direct/non-pooled Neon connection and PostgreSQL 18 client tools, restore to an empty target, verify schema `20261002_0023` and owned data, then run controlled target QA before opening writes.

After any new target writes, do not simply point traffic back to stale Neon. Preserve target changes and use a reviewed reverse-transfer/repair plan.

## 9. Domain / email

Until DOMAIN-001 the Caddy default remains controlled HTTP smoke only. Public traffic requires a commercial domain, TLS, PUBLIC_BASE_URL/TRUSTED_HOSTS, OAuth callback updates and verified transactional email.

## 10. Explicit prohibitions

Without later owner authorization: no Terraform apply, no production SQL/dump/restore, no cloud resource creation, no Render/Neon/Yandex production configuration changes, no paid Standard activation, no real-data AI, and no claim of LEGAL_PASS/COMPLETE.
