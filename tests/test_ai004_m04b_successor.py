"""AI004-M04B: append-only successor attestation and negative tamper tests.

Synthetic local files only; NEVER connects to real databases, Neon, providers,
Terraform, Render or remote clouds.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.ai004_m04b_successor import (
    MANIFEST_PATH, MATCHING_TABLES, MIGRATION, NEW_FILES,
    PREDECESSOR_HASHES, PRESERVED_FILES,
    SCHEMA_FROM, SCHEMA_TO, SOURCE_COMMIT, SOURCE_TREE,
    M04BSuccessorError, approved_sha256,
    expected_schema_head, revision_is_authorized,
    successor_exists, validate_successor,
)
from scripts.host001_stage_c_revision_gate import (
    StageCRevisionGateError, check_revision_chain,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def package_copy(tmp_path):
    # Copy ONLY the expressly versioned successor sources and evidence,
    # so negative cases cannot mutate or reference real production files.
    paths = set(PREDECESSOR_HASHES) | NEW_FILES | PRESERVED_FILES | {MANIFEST_PATH}
    for relative in sorted(paths):
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dest)
    return tmp_path


def test_successor_preserves_exact_0023_parent_and_approved_0024_head():
    manifest = validate_successor(ROOT)
    assert successor_exists(ROOT)
    assert manifest["source_commit"] == SOURCE_COMMIT
    assert manifest["source_tree"] == SOURCE_TREE
    assert manifest["schema_from"] == SCHEMA_FROM
    assert manifest["schema_to"] == SCHEMA_TO
    assert expected_schema_head(ROOT, SCHEMA_FROM) == SCHEMA_TO
    assert revision_is_authorized(ROOT) is True
    assert manifest["provider_calls"] == 0
    assert manifest["legal_state"] == "DRAFT"
    assert manifest["production_migration"] == "NOT_RUN"
    assert manifest["deployment"] == "NOT_RUN"
    assert manifest["public_real_data_enabled"] is False
    assert set(manifest["reviewed_runtime_changes"]) == set(PREDECESSOR_HASHES)
    assert set(manifest["new_runtime_sha256"]) == NEW_FILES
    assert set(manifest["preserved_sha256"]) == PRESERVED_FILES
    assert len(manifest["reviewed_runtime_changes"]) == 18
    assert len(manifest["new_runtime_sha256"]) >= 11


def test_runtime_exact_sha_transition_is_allowed_only_after_manifest_verification():
    m = validate_successor(ROOT)
    for relative, predecessor in PREDECESSOR_HASHES.items():
        assert approved_sha256(ROOT, relative, predecessor) == (
            m["reviewed_runtime_changes"][relative]["current_sha256"]
        )
    assert approved_sha256(
        ROOT, "domain/ai.py",
        m["preserved_sha256"]["domain/ai.py"],
    ) == m["preserved_sha256"]["domain/ai.py"]
    with pytest.raises(M04BSuccessorError, match="^invalid_successor_predecessor$"):
        approved_sha256(ROOT, "database.py", "0" * 64)


def test_old_0023_behavior_is_preserved_without_successor_manifest(tmp_path):
    assert not successor_exists(tmp_path)
    assert expected_schema_head(tmp_path, SCHEMA_FROM) == SCHEMA_FROM
    assert approved_sha256(tmp_path, "database.py", "f" * 64) == "f" * 64
    with pytest.raises(M04BSuccessorError, match="^successor_evidence_missing$"):
        validate_successor(tmp_path)


@pytest.mark.parametrize("change", [
    "schema_to", "schema_from", "source_commit", "source_tree",
    "legal_state", "provider_calls", "deployment", "production_migration",
    "real_data", "extra_section", "missing_runtime", "extra_runtime",
    "previous_sha", "current_sha", "new_sha", "preserved_sha",
    "missing_new", "extra_new",
])
def test_manifest_mutations_fail_closed(package_copy, change):
    path = package_copy / MANIFEST_PATH
    d = json.loads(path.read_text())
    if change in ("schema_from", "schema_to"):
        d[change] = "20991231_9999"
    elif change == "source_commit":
        d["source_commit"] = "0" * 40
    elif change == "source_tree":
        d["source_tree"] = "0" * 40
    elif change == "legal_state":
        d["legal_state"] = "ACTIVE"
    elif change == "provider_calls":
        d["provider_calls"] = 1
    elif change == "deployment":
        d["deployment"] = "DONE"
    elif change == "production_migration":
        d["production_migration"] = "DONE"
    elif change == "real_data":
        d["public_real_data_enabled"] = True
    elif change == "extra_section":
        d["unreviewed_new_permission"] = True
    elif change == "missing_runtime":
        d["reviewed_runtime_changes"].pop("database.py")
    elif change == "extra_runtime":
        d["reviewed_runtime_changes"]["domain/ai.py"] = {
            "previous_sha256": "0" * 64, "current_sha256": "0" * 64,
        }
    elif change == "previous_sha":
        d["reviewed_runtime_changes"]["database.py"]["previous_sha256"] = "0" * 64
    elif change == "current_sha":
        d["reviewed_runtime_changes"]["database.py"]["current_sha256"] = "0" * 64
    elif change == "new_sha":
        d["new_runtime_sha256"][MIGRATION] = "0" * 64
    elif change == "preserved_sha":
        d["preserved_sha256"]["render.yaml"] = "0" * 64
    elif change == "missing_new":
        d["new_runtime_sha256"].pop(MIGRATION)
    else:
        d["new_runtime_sha256"]["routes/public_matching.py"] = "0" * 64
    path.write_text(json.dumps(d, ensure_ascii=False))
    with pytest.raises(M04BSuccessorError):
        validate_successor(package_copy)


@pytest.mark.parametrize("relative", [
    "database.py",
    "models/__init__.py",
    "repositories/privacy.py",
    "scripts/check_ai004_package.py",
    "scripts/check_job003_package.py",
    "scripts/host001_stage_c_fixture.py",
    "tests/test_priv001_migration.py",
    MIGRATION,
    "models/user_match.py",
    "render.yaml",
    "domain/ai.py",
    "docs/evidence/job-003/change_boundary.json",
    "scripts/host001_stage_c_revision_gate.py",
])
def test_edited_legacy_guard_policy_migration_or_evidence_is_detected(package_copy, relative):
    path = package_copy / relative
    path.write_bytes(path.read_bytes() + b"\n# malicious edited content")
    with pytest.raises(M04BSuccessorError):
        validate_successor(package_copy)


def test_drifted_revision_and_wrong_parent_cannot_be_claimed(package_copy):
    p = package_copy / MIGRATION
    code = p.read_text()
    p.write_text(code.replace(
        'down_revision = "20261002_0023"',
        'down_revision = "20261001_0022"',
    ))
    with pytest.raises(M04BSuccessorError):
        validate_successor(package_copy)
    with pytest.raises(M04BSuccessorError, match="^invalid_predecessor_schema$"):
        expected_schema_head(ROOT, "20261001_0022")


def test_host001_static_gate_reports_scoped_schema_only_after_successor():
    snapshot = check_revision_chain(ROOT)
    assert snapshot["revision"] == SCHEMA_TO
    assert snapshot["unique_head"] is True
    assert snapshot["matching_schema_coverage"] == "SCHEMA_INVENTORY_ONLY"
    assert MATCHING_TABLES <= set(
        # The static Stage C table list must be reviewed independently,
        # not derived dynamically from a migration or the manifest.
        _selected_schema_tables(ROOT)
    )


def _selected_schema_tables(root):
    import ast
    code = ast.parse((root / "scripts/host001_stage_c_fixture.py").read_text())
    for node in ast.walk(code):
        if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "selected_tables"
                        for target in node.targets)):
            return ast.literal_eval(node.value)
    raise AssertionError("static_stage_c_digest_missing")


def test_host001_rejects_missing_matching_backup_inventory_and_digest(package_copy):
    # Stage C's offline gate works on an exact, isolated schema tree. It does
    # not require a cloud resource or a provider credential.
    root = package_copy
    (root / "migrations/versions").mkdir(parents=True, exist_ok=True)
    for source in (ROOT / "migrations/versions").glob("*.py"):
        if source.name != Path(MIGRATION).name:
            shutil.copyfile(source, root / "migrations/versions" / source.name)
    assert check_revision_chain(root)["matching_schema_coverage"] == "SCHEMA_INVENTORY_ONLY"

    inventory = root / "operations/backup.py"
    original = inventory.read_text()
    inventory.write_text(original.replace('"user_match_cache",', '"deleted_matching_cache",'))
    with pytest.raises(StageCRevisionGateError, match="backup inventory"):
        check_revision_chain(root)
    inventory.write_text(original)
    stage_c = root / "scripts/host001_stage_c_fixture.py"
    stage_c.write_text(stage_c.read_text().replace('        "user_match_reports",\n',''))
    with pytest.raises(StageCRevisionGateError, match="schema digest omits"):
        check_revision_chain(root)
