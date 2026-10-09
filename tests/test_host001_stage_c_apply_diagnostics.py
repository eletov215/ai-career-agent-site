"""Offline regressions for sanitized HOST-001 Stage C apply diagnostics."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "infra/yandex-cloud/stage_c_apply_diagnostics.py"


def diagnostic_module():
    spec = importlib.util.spec_from_file_location("host001_stage_c_diagnostics", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StageCApplyDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = diagnostic_module()

    def test_classifies_a_reviewed_resource_without_echoing_sensitive_provider_text(self):
        secret = "VERY_PRIVATE_TEST_VALUE_497"
        request_id = "SHOULD_NOT_APPEAR_REQUEST_IDENTIFIER"
        log = (
            "Error: Provider error while creating an object: "
            f"PermissionDenied secret={secret}; RequestID={request_id}\n"
            "  with yandex_vpc_address.app,\n"
            "StatusCode: 403\n"
        )
        output = self.module.summarize(log)
        self.assertIn("IAM_PERMISSION", output)
        self.assertIn("yandex_vpc_address.app", output)
        self.assertIn("HTTP statuses: 403", output)
        self.assertNotIn(secret, output)
        self.assertNotIn(request_id, output)
        self.assertNotIn("Provider error while creating", output)

    def test_unknown_resource_or_message_cannot_enter_output(self):
        log = (
            "Error: PRIVATE_PASSWORD_ABCD PRIVATE_API_KEY_ABC\n"
            "  with yandex_cloud_unknown.PRIVATE_PASSWORD_ABCD,\n"
        )
        output = self.module.summarize(log)
        self.assertIn("UNCLASSIFIED", output)
        self.assertIn("Reviewed resource addresses: NONE_DETECTED", output)
        self.assertNotIn("PRIVATE_PASSWORD_ABCD", output)
        self.assertNotIn("PRIVATE_API_KEY_ABC", output)

    def test_multiple_classes_are_fixed_and_bounded(self):
        log = (
            "Error: QuotaExceeded and InvalidArgument; "
            "actual diagnostic includes token=NOT_FOR_PRINTING\n"
            "  with yandex_mdb_postgresql_cluster.main,\n"
            "StatusCode: 429\n"
        )
        output = self.module.summarize(log)
        self.assertIn("QUOTA_OR_CAPACITY", output)
        self.assertIn("INVALID_ARGUMENT", output)
        self.assertIn("yandex_mdb_postgresql_cluster.main", output)
        self.assertIn("HTTP statuses: 429", output)
        self.assertNotIn("NOT_FOR_PRINTING", output)

    def test_file_reader_does_not_leak_a_log_path_or_untrusted_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret-name.log"
            path.write_text(
                "Error: FailedPrecondition password=MY_TEST_PASSWORD\n"
                "  with yandex_storage_bucket.field_test[0],\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = self.module.main([str(path)])
            self.assertEqual(0, rc)
            self.assertIn("PREREQUISITE", output.getvalue())
            self.assertIn("yandex_storage_bucket.field_test[0]", output.getvalue())
            self.assertNotIn("secret-name.log", output.getvalue())
            self.assertNotIn("MY_TEST_PASSWORD", output.getvalue())

    def test_missing_log_is_reported_without_original_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sensitive-location-name"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = self.module.main([str(path)])
            self.assertEqual(0, rc)
            self.assertIn("could not be read", output.getvalue())
            self.assertNotIn(str(path), output.getvalue())


if __name__ == "__main__":
    unittest.main()
