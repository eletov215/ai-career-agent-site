# HOST-001 — Yandex Cloud Russia foundation

Status: **STAGE B IMPLEMENTED CANDIDATE / NO APPLY / NO PRODUCTION MIGRATION**.

Stage B (6 October 2026) prepares the owner-approved low-cost launch profile in code only. It does not create cloud resources.

This directory implements the owner decision of 24 September 2026: first launch
in Russia, audience 18+, Yandex Cloud as the target production cloud. It creates
a reviewable Terraform foundation only. Running `terraform apply` creates
billable resources and is a separate owner-authorized operation.

## Architecture

- Russia region only.
- One initial application VM in `ru-central1-d`, Ubuntu 24.04 LTS, reserved
  public IPv4, inbound 80/443 and SSH only from `admin_cidr`.
- Managed PostgreSQL 18 with an explicit `single` launch profile and a retained `two`-host future profile. Both remain private; the two-host profile enforces different Russia zones.
- Database port 6432 is reachable only from the application security group.
- Runtime secret metadata is stored in Yandex Lockbox. Terraform creates the
  secret container but **no secret payload values**.
- VM uses a linked service account with `lockbox.payloadViewer` only for that
  one secret. `run_with_lockbox.py` fetches values through VM metadata/IAM and
  injects them into the child process without writing a dotenv file.
- Yandex CA is installed on the host; the future `DATABASE_URL` must use
  `sslmode=verify-full`, port 6432 and the mounted CA path.
- The Yandex-specific Compose stack uses the managed database and keeps
  `AI_ENABLED=0`, `AI_KILL_SWITCH=1`, `AI_SYNTHETIC_ACCESS_ENABLED=0`.
- One web worker/VM is intentional while rate limiting remains process-local.
- Schema migration and background writers are opt-in Compose profiles; default/rehearsal startup does not mutate the database or run external synchronization/cleanup.
- Yandex backup/restore tools use PostgreSQL 18 clients and strict libpq TLS/primary-selection environment. Encrypted backup artifacts can be exported off-VM only through an explicit HTTPS presigned-object workflow.

## Validation without cloud spend

```bash
cd infra/yandex-cloud
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
python ../../scripts/check_host001_package.py
python -m unittest ../../tests/test_host001_package.py
```

CI performs only formatting, provider initialization, static validation and
unit/package checks. It must never run `terraform plan` with live credentials
or `terraform apply`.

## Before a later authorized apply

1. Create/select a dedicated Yandex Cloud Russia cloud/folder and review current
   pricing.
2. Set Yandex Cloud authentication outside Git and chat.
3. Copy only non-secret values from `terraform.tfvars.example`.
4. Set `TF_VAR_postgresql_app_password` through a protected local/CI secret
   channel. The write-only PostgreSQL attribute requires Terraform 1.11+ and
   avoids storing that password in Terraform state.
5. Run `terraform plan`, review the exact billable resources, then request
   owner authorization before apply.
6. After apply, add the Lockbox payload outside Terraform. At minimum the
   application needs `DATABASE_URL`, `FLASK_SECRET_KEY`,
   `TOKEN_ENCRYPTION_KEY`, provider/OAuth credentials required by current
   production startup, `SYNC_SECRET`, and deployment host settings.
7. Construct `DATABASE_URL` against the `postgresql_rw_fqdn` output on port
   6432 with `sslmode=verify-full`, `target_session_attrs=read-write`, and
   `sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem`.
8. Do not add Alice real-data credentials and do not change
   `REAL_DATA_SUPPORTED=False` in HOST-001.
9. Deploy the repository separately. Do **not** use a broad `--profile migration up` command. After loading the approved Lockbox secret, run only the migration service explicitly:

   ```bash
   python infra/yandex-cloud/run_with_lockbox.py -- \
     docker compose -f infra/yandex-cloud/compose.yaml run --rm --build migrate
   ```

   After the migration/restore checks succeed, start only the normal web path:

   ```bash
   python infra/yandex-cloud/run_with_lockbox.py -- \
     docker compose -f infra/yandex-cloud/compose.yaml up -d --build web gateway
   ```

   Enable background writers only after database revision/data checks pass:

   ```bash
   python infra/yandex-cloud/run_with_lockbox.py -- \
     docker compose -f infra/yandex-cloud/compose.yaml --profile writers \
     up -d --build sync-worker privacy-worker
   ```
10. Until DOMAIN-001, use only synthetic/owner-controlled smoke data. The
    default Caddy site is HTTP `:80`; commercial traffic requires DOMAIN-001
    TLS and reviewed public URLs.

## Gates still outside HOST-001

- No migration of Render/Neon production data (MIG-001).
- No production backup/restore drill or offsite backup destination (OPS-002).
- No commercial domain/TLS identity (DOMAIN-001).
- No final operator/legal entity, Terms, Privacy Policy or AI consent.
- No real-data Alice call, no payment processing, no Standard activation.

## Official Yandex Cloud references checked 24 September 2026

- Regions: https://yandex.cloud/en/docs/overview/concepts/region
- Availability zones: https://yandex.cloud/en/docs/overview/concepts/geo-scope
- Terraform provider release notes: https://yandex.cloud/en/docs/terraform/release-notes
- Managed PostgreSQL Terraform reference: https://yandex.cloud/en/docs/managed-postgresql/tf-ref
- PostgreSQL HA: https://yandex.cloud/en/docs/managed-postgresql/concepts/high-availability
- PostgreSQL connection/security groups: https://yandex.cloud/en/docs/managed-postgresql/operations/connect/
- Lockbox on VM: https://yandex.cloud/en/docs/compute/operations/vm-create/create-with-lockbox-secret
- Ubuntu 24.04 LTS image family: https://yandex.cloud/en/marketplace/products/yc/ubuntu-24-04-lts
