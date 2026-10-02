#!/usr/bin/env python3
"""Fail-closed JOB-002 successor boundary chained to the accepted main baseline."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "a11ac07b09addd32f3a3e26cec4e4296dbe85ab6"
SOURCE_TREE = "52eb37b839d42df8b5c9e8192c5716c1dbf523af"
EVIDENCE = "docs/evidence/job-002/change_boundary.json"
EXISTING_RUNTIME = {
    "app.py", "database.py", "models/__init__.py", "operations/backup.py",
    "repositories/privacy.py", "services/privacy.py", "services/storage.py",
    "templates/saved_vacancies/detail.html",
}
NEW_RUNTIME = {
    "domain/application_tracker.py", "models/application_tracker.py",
    "repositories/application_trackers.py", "services/application_trackers.py",
    "routes/application_trackers.py",
    "migrations/versions/20261001_0022_application_tracker.py",
    "templates/application_trackers/detail.html", "templates/application_trackers/error.html",
}
GUARD_CHANGES = {
    "scripts/check_ai001_package.py", "scripts/check_ai002_package.py",
    "scripts/check_ai003_package.py", "scripts/check_ai004_package.py",
    "scripts/check_ai005_package.py", "scripts/check_ai005_live_qa_boundary.py",
    "scripts/check_ai005_site_qa_package.py",
    "scripts/check_job001_package.py", "scripts/check_legal001_package.py",
    "scripts/legal001_boundary.py",
}
REQUIRED = NEW_RUNTIME | {
    "tests/test_job002_service.py", "tests/test_job002_routes.py",
    "tests/test_job002_migration.py", "tests/test_job002_package.py",
    "docs/JOB002_IMPLEMENTATION.md", "docs/JOB002_RUNBOOK.md",
    "docs/JOB002_VERIFICATION_STATUS.md", EVIDENCE,
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _matches(path: Path, expected: str) -> bool:
    raw = path.read_bytes()
    return expected in {
        hashlib.sha256(raw).hexdigest(),
        hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
    }


def successor_hashes(root: Path = ROOT) -> dict[str, dict[str, str]]:
    evidence = json.loads((root / EVIDENCE).read_text())
    if (
        evidence.get("package") != "JOB-002"
        or evidence.get("source_commit") != SOURCE_COMMIT
        or evidence.get("source_tree") != SOURCE_TREE
        or evidence.get("schema_from") != "20260922_0021"
        or evidence.get("schema_to") != "20261001_0022"
        or evidence.get("legal_state") != "DRAFT"
        or evidence.get("public_real_data_enabled") is not False
        or evidence.get("provider_calls") != 0
        or evidence.get("production_migration") != "NOT_RUN"
        or set(evidence.get("reviewed_runtime_changes", {})) != EXISTING_RUNTIME
        or set(evidence.get("new_runtime_sha256", {})) != NEW_RUNTIME
        or set(evidence.get("authorized_guard_changes", {})) != GUARD_CHANGES
    ):
        raise ValueError("Invalid JOB-002 successor evidence")
    rows = {
        **evidence["reviewed_runtime_changes"],
        **evidence["authorized_guard_changes"],
    }
    successor_path = root / "docs/evidence/job-003/change_boundary.json"
    successor = json.loads(successor_path.read_text()) if successor_path.is_file() else {}
    authorized = {**successor.get("reviewed_runtime_changes", {}),
                  **successor.get("authorized_guard_changes", {})} if (
        successor.get("package") == "JOB-003"
        and successor.get("source_commit") == "8001efbd4c70144bdeab2bdf8e3f64b00bf9c179"
        and successor.get("schema_from") == "20261001_0022"
    ) else {}
    for rel, row in rows.items():
        direct = _matches(root / rel, row["current_sha256"])
        next_row = authorized.get(rel, {})
        chained = (next_row.get("previous_sha256") == row["current_sha256"]
                   and _matches(root / rel, next_row.get("current_sha256", "")))
        if set(row) != {"previous_sha256", "current_sha256"} or not (direct or chained):
            raise ValueError("JOB-002 changed-file hash mismatch: " + rel)
    for rel, digest in evidence["new_runtime_sha256"].items():
        next_row = authorized.get(rel, {})
        chained = (next_row.get("previous_sha256") == digest
                   and _matches(root / rel, next_row.get("current_sha256", "")))
        if not (_matches(root / rel, digest) or chained):
            raise ValueError("JOB-002 new-file hash mismatch: " + rel)
    return rows


def validate(root: Path = ROOT) -> list[str]:
    errors = [f"missing:{path}" for path in sorted(REQUIRED) if not (root / path).is_file()]
    try:
        successor_hashes(root)
        checks = {
            "database.py": 'CURRENT_REVISION = "20261002_0023"',
            "domain/ai.py": "REAL_DATA_SUPPORTED = False",
            "migrations/versions/20261001_0022_application_tracker.py":
                "down_revision = '20260922_0021'",
            "services/legal_policy.py": 'release_state="DRAFT"',
        }
        for path, needle in checks.items():
            if needle not in (root / path).read_text():
                errors.append(f"boundary:{path}")
        migration = (root / "migrations/versions/20261001_0022_application_tracker.py").read_text()
        tree = ast.parse(migration)
        tables = {
            node.args[0].value for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "create_table" and node.args
            and isinstance(node.args[0], ast.Constant)
        }
        if tables != {"saved_vacancy_trackers", "saved_vacancy_tracker_events"}:
            errors.append("migration:unexpected_tables")
        workflow = (root / ".github/workflows/job002.yml").read_text()
        if "python scripts/check_job002_package.py" not in workflow:
            errors.append("job002_ci:missing_package_gate")
        for path in (root / ".github/workflows").glob("*.yml"):
            source = path.read_text()
            if ("AI_BENCH_YANDEX" in source or "ALICE" in source) and "workflow_dispatch" not in source:
                errors.append("billable_workflow_not_dispatch_only:" + path.name)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        errors.append("successor:" + str(exc))
    return errors


if __name__ == "__main__":
    failures = validate()
    print(json.dumps({
        "package": "JOB-002", "ok": not failures, "errors": failures,
        "source_commit": SOURCE_COMMIT, "source_tree": SOURCE_TREE,
        "legal_state": "DRAFT", "real_data_enabled": False, "provider_calls": 0,
        "production_migration": "NOT_RUN", "remote_ci": "NOT_ATTESTED_BY_LOCAL_CHECK",
    }, indent=2))
    raise SystemExit(bool(failures))
