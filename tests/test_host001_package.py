from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
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

    def test_yandex_proxy_rebuilds_trusted_client_header(self):
        caddy = (ROOT / "infra/yandex-cloud/Caddyfile").read_text(encoding="utf-8")
        self.assertIn("header_up -CF-Connecting-IP", caddy)
        self.assertIn("header_up X-Forwarded-For {http.request.remote.host}", caddy)

    def test_rehearsal_default_does_not_auto_start_writers_or_migration(self):
        compose = (ROOT / "infra/yandex-cloud/compose.yaml").read_text(encoding="utf-8")
        self.assertIn('profiles: ["migration"]', compose)
        self.assertGreaterEqual(compose.count('profiles: ["writers"]'), 2)
        self.assertNotIn("depends_on:\n      migrate:", compose)


class BackupExportTests(unittest.TestCase):
    @staticmethod
    def _module():
        path = ROOT / "infra/yandex-cloud/export_backup_s3.py"
        spec = importlib.util.spec_from_file_location("host001_backup_export", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_exporter_rejects_non_https_presigned_url(self):
        module = self._module()
        with self.assertRaises(module.ExportError):
            module.validate_presigned_url("http://storage.example.test/object")

    def test_exporter_requires_encrypted_matching_manifest(self):
        module = self._module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "sample.dump.enc"
            backup.write_bytes(b"encrypted-bytes")
            import hashlib
            manifest = root / "sample.dump.enc.manifest.json"
            manifest.write_text(json.dumps({
                "encrypted": True,
                "backup_file": backup.name,
                "size_bytes": backup.stat().st_size,
                "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
            }), encoding="utf-8")
            module.verify_encrypted_backup(backup, manifest)

            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["encrypted"] = False
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(module.ExportError):
                module.verify_encrypted_backup(backup, manifest)


class LockboxLoaderTests(unittest.TestCase):
    @staticmethod
    def _module():
        path = ROOT / "infra/yandex-cloud/run_with_lockbox.py"
        spec = importlib.util.spec_from_file_location("host001_lockbox", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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
