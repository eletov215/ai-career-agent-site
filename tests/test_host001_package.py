from __future__ import annotations

import base64
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts.check_host001_package import ROOT, validate


class Host001PackageTests(unittest.TestCase):
    def test_repository_candidate_passes_static_guard(self):
        self.assertEqual([], validate(ROOT))

    def test_stage_b_single_profile_keeps_future_two_host_path(self):
        variables = (ROOT / "infra/yandex-cloud/variables.tf").read_text(encoding="utf-8")
        main = (ROOT / "infra/yandex-cloud/main.tf").read_text(encoding="utf-8")
        self.assertIn('default     = "single"', variables)
        self.assertIn('contains(["single", "two"], var.postgresql_host_profile)', variables)
        self.assertIn('version                   = 18', main)
        self.assertIn('dynamic "host"', main)
        self.assertIn('var.postgresql_host_profile == "two"', main)

    def test_stage_c_field_resources_are_opt_in_and_teardown_safe(self):
        variables = (ROOT / "infra/yandex-cloud/variables.tf").read_text(encoding="utf-8")
        main = (ROOT / "infra/yandex-cloud/main.tf").read_text(encoding="utf-8")
        example = (ROOT / "infra/yandex-cloud/terraform.stage-c.tfvars.example").read_text(
            encoding="utf-8"
        )
        self.assertIn('variable "field_test_resources_enabled"', variables)
        self.assertIn('variable "foundation_deletion_protection"', variables)
        self.assertIn('resource "yandex_storage_bucket" "field_test"', main)
        self.assertIn(
            'resource "yandex_mdb_postgresql_cluster" "field_test_restore"',
            main,
        )
        self.assertIn(
            'resource "yandex_iam_service_account_static_access_key" "field_test_storage"',
            main,
        )
        self.assertIn("output_to_lockbox {", main)
        self.assertIn('role        = "storage.uploader"', main)
        self.assertIn("force_destroy         = true", main)
        self.assertIn(
            "!var.field_test_resources_enabled || !var.foundation_deletion_protection",
            main,
        )
        self.assertIn("field_test_resources_enabled  = true", example)
        self.assertIn("foundation_deletion_protection = false", example)

    def test_stage_c_workflow_keeps_credentials_step_scoped_and_actions_pinned(self):
        workflow = (ROOT / ".github/workflows/host001-stage-c-plan.yml").read_text(
            encoding="utf-8"
        )
        job_env = workflow.split("    env:\n", 1)[1].split("    steps:\n", 1)[0]
        self.assertNotIn("secrets.", job_env)
        self.assertIn("actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803", workflow)
        self.assertIn(
            "hashicorp/setup-terraform@b9cd54a3c349d3f38e8881555d616ced269862dd",
            workflow,
        )

    def test_stage_c_guard_rejects_security_boundary_regressions(self):
        workflow_path = ROOT / ".github/workflows/host001-stage-c-plan.yml"
        original = workflow_path.read_text(encoding="utf-8")
        cloud_binding = "          TF_VAR_cloud_id: ${{ secrets.YC_STAGE_C_CLOUD_ID }}\n"
        plan_shell = "      - name: Credentialed Stage C plan\n        id: plan\n        shell: bash\n"
        summary_step = (
            "      - name: Emit secret-free resource/action summary and reject destructive plan\n"
        )
        mutations = {
            "job-scoped secret": original.replace(
                "    env:\n", "    env:\n      LEAK: ${{ secrets.YC_STAGE_C_CLOUD_ID }}\n", 1
            ),
            "duplicate secret": original.replace(
                cloud_binding, cloud_binding + "          DUPLICATE: ${{ secrets.YC_STAGE_C_CLOUD_ID }}\n", 1
            ),
            "commented required secret": original.replace(
                cloud_binding, "          # " + cloud_binding.lstrip(), 1
            ),
            "unnamed action wrong-step secret": original.replace(cloud_binding, "", 1).replace(
                summary_step,
                "      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803\n"
                "        env:\n"
                "          MOVED_CLOUD_ID: ${{ secrets.YC_STAGE_C_CLOUD_ID }}\n\n"
                + summary_step,
                1,
            ),
            "mutable action": original.replace(
                "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
                "actions/checkout@v6",
            ),
            "named mutable action": original.replace(
                "      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6",
                "      - name: Checkout\n        uses: actions/checkout@v6",
            ),
            "named artifact upload": original + (
                "\n      - name: Upload plan\n"
                "        uses: actions/upload-artifact@65c4c4a1ddee5b72f698fdd19549f0f0fb45cf08\n"
            ),
            "secret-bearing named action": original.replace(
                plan_shell,
                "      - name: Credentialed Stage C plan\n"
                "        id: plan\n"
                "        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803\n",
                1,
            ),
            "terraform apply": original + "\n      terraform apply\n",
            "terraform destroy": original + "\n      terraform destroy\n",
            "artifact upload": original + "\n      - uses: actions/upload-artifact@v4\n",
            "unescaped summary SHA": original.replace(
                'echo "- Commit: \\`$GITHUB_SHA\\`"',
                'echo "- Commit: `$GITHUB_SHA`"',
            ),
        }
        for label, mutated in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for path in ROOT.iterdir():
                    if path.name != ".git":
                        (root / path.name).symlink_to(path, target_is_directory=path.is_dir())
                local_workflows = root / ".github" / "workflows"
                (root / ".github").unlink()
                local_workflows.mkdir(parents=True)
                for path in (ROOT / ".github" / "workflows").iterdir():
                    (local_workflows / path.name).symlink_to(path)
                (local_workflows / workflow_path.name).unlink()
                (local_workflows / workflow_path.name).write_text(mutated, encoding="utf-8")
                errors = validate(root)
                self.assertTrue(errors, label)
                if label == "unnamed action wrong-step secret":
                    self.assertIn(
                        "Stage C secret YC_STAGE_C_CLOUD_ID is bound to the wrong step",
                        errors,
                    )
                if label == "commented required secret":
                    self.assertIn(
                        "Stage C secret YC_STAGE_C_CLOUD_ID must be bound exactly once", errors
                    )
                if label == "secret-bearing named action":
                    self.assertIn(
                        "Stage C secret YC_STAGE_C_CLOUD_ID must be bound to a trusted shell step",
                        errors,
                    )
                if label == "named mutable action":
                    self.assertIn(
                        "Stage C action actions/checkout must use an immutable commit SHA", errors
                    )
                if label == "named artifact upload":
                    self.assertIn("Stage C workflow must not upload artifacts", errors)

    def test_stage_c_apply_workflow_is_manual_bounded_and_auto_tears_down(self):
        workflow = (ROOT / ".github/workflows/host001-stage-c-apply.yml").read_text(
            encoding="utf-8"
        )
        job_env = workflow.split("    env:\n", 1)[1].split("    steps:\n", 1)[0]
        self.assertNotIn("secrets.", job_env)
        self.assertIn("APPLY_STAGE_C_SYNTHETIC_1000_RUB_4H", workflow)
        self.assertIn('test "$STAGE_C_HOLD_MINUTES" -le 180', workflow)
        self.assertIn("trap cleanup EXIT", workflow)
        self.assertIn("terraform -chdir=infra/yandex-cloud destroy", workflow)
        self.assertIn("Stage C teardown verified: no managed Terraform resources remain.", workflow)
        self.assertNotIn("actions/upload-artifact", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  pull_request:", workflow)

    def test_stage_c_apply_guard_rejects_boundary_regressions(self):
        workflow_path = ROOT / ".github/workflows/host001-stage-c-apply.yml"
        original = workflow_path.read_text(encoding="utf-8")
        cloud_binding = "          TF_VAR_cloud_id: ${{ secrets.YC_STAGE_C_CLOUD_ID }}\n"
        mutations = {
            "wrong acknowledgement": original.replace(
                "APPLY_STAGE_C_SYNTHETIC_1000_RUB_4H",
                "APPLY_STAGE_C_UNBOUNDED",
            ),
            "oversized hold": original.replace(
                'test "$STAGE_C_HOLD_MINUTES" -le 180',
                'test "$STAGE_C_HOLD_MINUTES" -le 600',
            ),
            "job-scoped secret": original.replace(
                "    env:\n",
                "    env:\n      LEAK: ${{ secrets.YC_STAGE_C_CLOUD_ID }}\n",
                1,
            ),
            "duplicate cloud secret": original.replace(
                cloud_binding,
                cloud_binding + "          DUPLICATE: ${{ secrets.YC_STAGE_C_CLOUD_ID }}\n",
                1,
            ),
            "mutable checkout": original.replace(
                "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
                "actions/checkout@v6",
            ),
            "artifact upload": original + (
                "\n      - name: Upload state\n"
                "        uses: actions/upload-artifact@v4\n"
            ),
            "missing emergency destroy": original.replace(
                "terraform -chdir=infra/yandex-cloud destroy \\\n",
                "terraform -chdir=infra/yandex-cloud plan \\\n",
                1,
            ),
        }
        for label, mutated in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for path in ROOT.iterdir():
                    if path.name != ".git":
                        (root / path.name).symlink_to(path, target_is_directory=path.is_dir())
                local_workflows = root / ".github" / "workflows"
                (root / ".github").unlink()
                local_workflows.mkdir(parents=True)
                for path in (ROOT / ".github" / "workflows").iterdir():
                    (local_workflows / path.name).symlink_to(path)
                (local_workflows / workflow_path.name).unlink()
                (local_workflows / workflow_path.name).write_text(mutated, encoding="utf-8")
                errors = validate(root)
                self.assertTrue(errors, label)

    def test_yandex_proxy_rebuilds_trusted_client_header(self):
        caddy = (ROOT / "infra/yandex-cloud/Caddyfile").read_text(encoding="utf-8")
        self.assertIn("header_up -CF-Connecting-IP", caddy)
        self.assertIn("header_up X-Forwarded-For {http.request.remote.host}", caddy)

    def test_rehearsal_default_does_not_auto_start_writers_or_migration(self):
        compose = (ROOT / "infra/yandex-cloud/compose.yaml").read_text(encoding="utf-8")
        self.assertIn('profiles: ["migration"]', compose)
        self.assertGreaterEqual(compose.count('profiles: ["writers"]'), 2)
        self.assertNotIn("depends_on:\n      migrate:", compose)
        for name in (
            "BACKUP_EXPORT_FILE",
            "BACKUP_EXPORT_MANIFEST",
            "BACKUP_S3_PRESIGNED_URL",
            "BACKUP_S3_MANIFEST_PRESIGNED_URL",
        ):
            self.assertIn("${" + name + ":-}", compose)
            self.assertNotIn("${" + name + ":?", compose)


class BackupExportTests(unittest.TestCase):
    @staticmethod
    def _module():
        path = ROOT / "infra/yandex-cloud/export_backup_s3.py"
        spec = importlib.util.spec_from_file_location("host001_backup_export", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _manifest(backup: Path) -> dict[str, object]:
        import hashlib

        return {
            "encrypted": True,
            "backup_file": backup.name,
            "size_bytes": backup.stat().st_size,
            "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        }

    def test_exporter_rejects_non_https_presigned_url(self):
        module = self._module()
        with self.assertRaises(module.ExportError):
            module.validate_presigned_url("http://storage.example.test/object")

    def test_exporter_rejects_duplicate_object_target_with_different_signatures(self):
        module = self._module()
        backup_url = "https://storage.example.test/bucket/same-object?signature=one"
        manifest_url = "https://storage.example.test/bucket/same-object?signature=two"
        with self.assertRaises(module.ExportError):
            module.validate_distinct_object_targets(backup_url, manifest_url)

    def test_exporter_rejects_same_yandex_object_across_url_aliases(self):
        module = self._module()
        backup_url = (
            "https://aca-backups.storage.yandexcloud.net/prod/backup.dump.enc"
            "?X-Amz-Signature=one"
        )
        manifest_url = (
            "https://storage.yandexcloud.net/aca-backups/prod/backup.dump.enc"
            "?X-Amz-Signature=two"
        )
        with self.assertRaises(module.ExportError):
            module.validate_distinct_object_targets(backup_url, manifest_url)

    def test_exporter_generates_short_lived_yandex_put_urls_without_secret(self):
        module = self._module()
        url = module.generate_presigned_put_url(
            "aca-field-backup-example",
            "field-test/sample.dump.enc",
            "YCAJEXAMPLEACCESS",
            "do-not-leak-secret",
            expires_seconds=900,
            now=datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(url.startswith("https://storage.yandexcloud.net/"))
        self.assertIn("X-Amz-Algorithm=AWS4-HMAC-SHA256", url)
        self.assertIn("X-Amz-Expires=900", url)
        self.assertIn("X-Amz-Signature=", url)
        self.assertNotIn("do-not-leak-secret", url)

    def test_exporter_generates_distinct_backup_and_manifest_targets(self):
        module = self._module()
        with mock.patch.dict(
            module.os.environ,
            {
                "BACKUP_S3_BUCKET": "aca-field-backup-example",
                "BACKUP_S3_ACCESS_KEY": "YCAJEXAMPLEACCESS",
                "BACKUP_S3_SECRET_KEY": "secret",
                "BACKUP_S3_OBJECT_PREFIX": "field-test",
            },
            clear=False,
        ):
            with mock.patch.object(
                module,
                "generate_presigned_put_url",
                side_effect=[
                    "https://storage.yandexcloud.net/aca-field-backup-example/field-test/a?sig=1",
                    "https://storage.yandexcloud.net/aca-field-backup-example/field-test/b?sig=2",
                ],
            ):
                backup_url, manifest_url = module._resolve_upload_urls(
                    Path("backup.dump.enc"),
                    Path("backup.dump.enc.manifest.json"),
                )
        self.assertNotEqual(
            module._object_target_identity(backup_url),
            module._object_target_identity(manifest_url),
        )

    def test_exporter_sanitizes_timeout_without_presigned_url(self):
        module = self._module()
        secret_url = "https://storage.example.test/object?signature=do-not-log"
        with mock.patch.object(
            module.subprocess,
            "run",
            side_effect=module.subprocess.TimeoutExpired(
                ["curl", "--upload-file", "/tmp/example", secret_url],
                1800,
            ),
        ):
            with self.assertRaises(module.ExportError) as caught:
                module._upload(Path("/tmp/example"), secret_url)
        self.assertNotIn(secret_url, str(caught.exception))
        self.assertNotIn("signature=", str(caught.exception))

    def test_exporter_rejects_fake_enc_extension_without_encryption_envelope(self):
        module = self._module()
        with tempfile.TemporaryDirectory() as tmp:
            backup = Path(tmp) / "sample.dump.enc"
            backup.write_bytes(b"plaintext-renamed-as-encrypted")
            with self.assertRaises(module.ExportError):
                module.validate_encryption_envelope(backup)

    def test_exporter_authenticates_aes_gcm_before_upload(self):
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        module = self._module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "sample.dump.enc"
            manifest = root / "sample.dump.enc.manifest.json"
            key = b"K" * 32
            nonce = b"N" * 12
            encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
            ciphertext = encryptor.update(b"synthetic-postgres-dump") + encryptor.finalize()
            backup.write_bytes(b"ACAOPS1" + nonce + ciphertext + encryptor.tag)
            manifest.write_text(
                json.dumps(self._manifest(backup)),
                encoding="utf-8",
            )
            encoded_key = base64.urlsafe_b64encode(key).decode("ascii")

            module.verify_encrypted_backup(
                backup,
                manifest,
                encryption_key=encoded_key,
            )

            tampered = bytearray(backup.read_bytes())
            tampered[-1] ^= 1
            backup.write_bytes(bytes(tampered))
            manifest.write_text(
                json.dumps(self._manifest(backup)),
                encoding="utf-8",
            )
            with self.assertRaises(module.ExportError):
                module.verify_encrypted_backup(
                    backup,
                    manifest,
                    encryption_key=encoded_key,
                )

    def test_exporter_rejects_manifest_that_claims_plaintext(self):
        module = self._module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "sample.dump.enc"
            backup.write_bytes(b"ACAOPS1" + b"N" * 12 + b"C" + b"T" * 16)
            manifest = root / "sample.dump.enc.manifest.json"
            payload = self._manifest(backup)
            payload["encrypted"] = False
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(module.ExportError):
                module.verify_encrypted_backup(
                    backup,
                    manifest,
                    encryption_key=base64.urlsafe_b64encode(b"K" * 32).decode("ascii"),
                )


class LockboxLoaderTests(unittest.TestCase):
    @staticmethod
    def _module():
        path = ROOT / "infra/yandex-cloud/run_with_lockbox.py"
        spec = importlib.util.spec_from_file_location("host001_lockbox", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_yandex_database_url_requires_verify_full_ca_and_primary(self):
        module = self._module()
        module.validate_database_url(
            "postgresql+psycopg://user:secret@db.example.test:6432/aca"
            "?sslmode=verify-full"
            "&sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem"
            "&target_session_attrs=read-write"
        )
        for weak_url in (
            "postgresql+psycopg://user:secret@db.example.test:6432/aca"
            "?sslmode=require"
            "&sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem"
            "&target_session_attrs=read-write",
            "postgresql+psycopg://user:secret@db.example.test:6432/aca"
            "?sslmode=verify-full"
            "&target_session_attrs=read-write",
            "postgresql+psycopg://user:secret@db.example.test:6432/aca"
            "?sslmode=verify-full"
            "&sslrootcert=/etc/ssl/certs/yandex-cloud-ca.pem"
            "&target_session_attrs=any",
        ):
            with self.assertRaises(module.SecretLoadError):
                module.validate_database_url(weak_url)

    def test_loader_parses_allowlisted_environment_shape_without_printing(self):
        module = self._module()
        calls = [
            {"access_token": "iam-token"},
            {"entries": [
                {"key": "DATABASE_URL", "textValue": "postgresql+psycopg://example"},
                {"key": "FLASK_SECRET_KEY", "textValue": "secret-value"},
            ]},
        ]
        with mock.patch.object(module, "_json_get", side_effect=calls):
            result = module.load_secret_entries("e6q123456789")
        self.assertEqual(
            result,
            {
                "DATABASE_URL": "postgresql+psycopg://example",
                "FLASK_SECRET_KEY": "secret-value",
            },
        )

    def test_loader_rejects_duplicate_keys(self):
        module = self._module()
        calls = [
            {"access_token": "iam-token"},
            {"entries": [
                {"key": "DATABASE_URL", "textValue": "one"},
                {"key": "DATABASE_URL", "textValue": "two"},
            ]},
        ]
        with mock.patch.object(module, "_json_get", side_effect=calls):
            with self.assertRaises(module.SecretLoadError):
                module.load_secret_entries("e6q123456789")

    def test_loader_rejects_invalid_environment_key(self):
        module = self._module()
        calls = [
            {"access_token": "iam-token"},
            {"entries": [{"key": "bad-key", "textValue": "value"}]},
        ]
        with mock.patch.object(module, "_json_get", side_effect=calls):
            with self.assertRaises(module.SecretLoadError):
                module.load_secret_entries("e6q123456789")


if __name__ == "__main__":
    unittest.main()
