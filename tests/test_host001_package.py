from __future__ import annotations

import importlib.util
import unittest
from unittest import mock

from scripts.check_host001_package import ROOT, validate


class Host001PackageTests(unittest.TestCase):
    def test_repository_candidate_passes_static_guard(self):
        self.assertEqual([], validate(ROOT))


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
