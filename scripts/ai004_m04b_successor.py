"""AI004-M04B: fail-closed additive schema successor, no live operations.

Historical evidence is immutable. A new, strictly scoped review manifest
authorises only 0023 -> 0024 and exact source-file SHA256 transitions.
This module uses Python stdlib only: no database, provider, cloud or network.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

SCHEMA_FROM = "20261002_0023"
SCHEMA_TO = "20261009_0024"
SOURCE_COMMIT = "a0166cdcb9087b3e5525ad6748e23d5ec0604913"
SOURCE_TREE = "4c5343f5c70a0ea945e87b1786e878757174855d"
MANIFEST_PATH = "docs/evidence/ai-004/m04b-successor/change_boundary.json"
MIGRATION = "migrations/versions/20261009_0024_user_matching_cache.py"
MATCHING_TABLES = frozenset(("user_match_reports", "user_match_cache"))

# Exact prior hashes of the reviewed 0023 main commit, NOT copied from or
# replaceable by the new manifest. Existing JOB-002/003/004 guards also attest
# the overlapping accepted predecessors.
PREDECESSOR_HASHES = {
    # Only the unprivileged PR-only CI workflow may attest an expected denial.
    # The manual Stage C apply workflow and Python preflight stay protected.
    ".github/workflows/host001-yandex-cloud.yml": "3fedd28efd7a32cac33143c509d59066f6715c033634d069e0108205961f4dc9",
    "database.py": "467a7223a9efc8a75cc7fb1d83aa1382996d0f5e0cf1b0ae1510f17b8a5cdede",
    "models/__init__.py": "029c6e0225213fa1a1ca19fa8b08302d0532a56e14aea342b7533d4cc0a2c20e",
    "operations/backup.py": "c01b814f52fe3220d08fcbe9ec6aefd58ccd4d17e03ccfd6a5907c71d0428cc4",
    "repositories/privacy.py": "79e361d66186cc6d92ff5a03d2f0e885a63a900c7ecc7b73663579ce4b54ec46",
    "services/privacy.py": "e87455f07590c310a8d87b0e4f8ed663a3d4e3a8baa29d32d7a6bf444b0e6e6c",
    "scripts/check_ai001_package.py": "ee69cc4b366ca771214aeb44fd3713e35447b371ebf033161478ca0e44d27fe7",
    "scripts/check_ai002_package.py": "291a1241a1163819e1f3ef3c7b4c4e9e3dd8d6e17297dba06489f88e5c9a8171",
    "scripts/check_ai003_package.py": "86e6fba68c541df4666b0b8487a651cf9f923cfeaa0408f798d1cf22953346c9",
    "scripts/check_ai004_package.py": "5c8070558cc9308def01940f7df25d1e5e1787c42527109d39f84cc455835d35",
    "scripts/check_ai005_package.py": "04f0a1960bb15d7bcf87f511f84b9f363203996189c8fd29e7c40052770ac90a",
    "scripts/check_job001_package.py": "20d77a0f5a4ea00decf590e336c19160b0358e0d1655bdf815e62c30bc679601",
    "scripts/check_job002_package.py": "603f0ef5e9ac018c2a731bdd415951d40b585df65690392e35dd3793bd98963e",
    "scripts/check_job003_package.py": "97ba849106dca2ffa20cbd3bc95740636b17f019091de3a0b8d89e71bcca6f3e",
    "scripts/check_job004_package.py": "0333134d74341ac3f3a41032ff923076ef833c3f2317aa87d5047caca77abc19",
    "scripts/check_legal001_package.py": "6613b671309a6224d0dd616c2ace9c02007972e9d5c56dfe26df186c14c03aa1",
    "scripts/host001_stage_c_fixture.py": "f609623abb53a4847312da8303ae7f7edd99cb48fd809173122c5be7ddb6edd2",
    "tests/test_priv001_migration.py": "76e5a41f427400feba1b58b1cd61741a307bbd15daa9dd83a435fd6820b44c9d",
    "tests/test_legal001_postgresql.py": "753882d46bf39457af9b92d431644b4eb6ab95aac57e9adecfb8ce71da107445",
    "tests/test_job003_migration.py": "5d3993671559e54e179d61f1e4817592fe702129f33c90f2e96b5c1eb9280013",
    "tests/ai005_boundary_helper.py": "f442fed149d7e935d2afe00ba55ce5374e2c5fe9fbc77d4ec3b26b2b913d8baa",
    "tests/test_ai005_site_qa_package.py": "7458770dbedd357b35c15f620134346aff5ecc3592b32bfdfd60b27ef084938a",
    "tests/test_legal001_migration.py": "0c765b7ed4ed12f42db882634d088932dd4a569fe73d41ad3d36f438ae96a90c",
    "tests/test_host001_stage_c_apply_gate.py": "3bc4f5b6fa0a0e836fd1092f029df205f35a7393d6a5d6ddf6a8d5f25a2fc4b6",
}

NEW_FILES = frozenset({
    ".github/workflows/ai004-m04b-candidate.yml",
    "docs/AI004_M04B_SCHEMA_SUCCESSOR_PROPOSAL_20261009.md",
    MIGRATION,
    "models/user_match.py",
    "repositories/user_match.py",
    "scripts/ai004_m04b_successor.py",
    "tests/test_ai004_m04b_migration.py",
    "tests/test_ai004_m04b_storage.py",
    "tests/test_ai004_m04b_restore.py",
    "tests/test_ai004_m04b_pg18_restore.py",
    "tests/test_ai004_m04b_successor.py",
})

# Historical artifacts and legal/cloud safety controls cannot be relabelled.
# SHA256s are separately pinned in PRESERVED_SHA256 below.
PRESERVED_FILES = frozenset({
    "docs/evidence/job-002/change_boundary.json",
    "docs/evidence/job-003/change_boundary.json",
    "docs/evidence/job-004/change_boundary.json",
    "docs/evidence/ai-004/change_boundary.json",
    "docs/evidence/legal-001/change_boundary.json",
    "domain/ai.py",
    "services/legal_policy.py",
    "render.yaml",
    "scripts/host001_stage_c_revision_gate.py",
    "tests/test_host001_stage_c_revision_gate.py",
    ".github/workflows/host001-stage-c-apply.yml",
    "scripts/host001_stage_c_apply_gate.py",
    "scripts/check_host001_package.py",
    "tests/test_host001_package.py",
    "docs/HOST001_STAGE_C_PREAPPLY_SCHEMA_GATE_20261009.md",
})
PRESERVED_SHA256 = {
    ".github/workflows/host001-stage-c-apply.yml": "cef3c8e6b5dc045cff47572a81e28f30daaec9e007a8427db0c6fc3d1508bc01",
    "scripts/host001_stage_c_apply_gate.py": "9c926266d9b2b1bb44a48f9134b564c67c5f267d9bad398ea4a123a0aab0177f",
    "scripts/check_host001_package.py": "272c8797ad528c1234fceb097f4fad25ab6c0c87740cb5c62676bfcbd9510e3b",
    "tests/test_host001_package.py": "fc3341df6625735e76f3bcc4832bb6b171e74b0c8c0e3081d7746c095aaf49e1",
    "docs/HOST001_STAGE_C_PREAPPLY_SCHEMA_GATE_20261009.md": "f293b25719ad401d859e5780f5458b63dbab3e66f900ad17b55d2d626dc51039",
    "docs/evidence/ai-004/change_boundary.json": "4a7afe4474275599ec1d06ead2fc37c5097dd6335963c40a7dfef20864e68626",
    "docs/evidence/job-002/change_boundary.json": "de1bc9616a892bc453af905924c63fb7e011bd6974ef17a9856cc028b64ac517",
    "docs/evidence/job-003/change_boundary.json": "2ba0897c4de4588802256a27f870cf6e8579afa52fbc3b3b3fdff6c5dd3da928",
    "docs/evidence/job-004/change_boundary.json": "530545f335126925018cbc0acd21dfdaccf183dcf3cba3da0d25e2deb8a65d77",
    "docs/evidence/legal-001/change_boundary.json": "6ff430dc4216c534c1bad1ce11e45ea98fb44edc94dca06557b338d798f78d94",
    "domain/ai.py": "d1b427bf73b8797a03f1254a83ec015c79121204c7198409151372d933fbd3aa",
    "render.yaml": "f61662adb273597df027195c2d28922c841b0f18fc6904e68258e46cb7cc0c37",
    "scripts/host001_stage_c_revision_gate.py": "abecb6c3a092472fa6a2c6be91737eba7315b24ca0d3ddc8263e2d47a3483466",
    "services/legal_policy.py": "b2ffbc0fb59954053b1c01008c360b41bccf78d902c8b00193202aee94218a2e",
    "tests/test_host001_stage_c_revision_gate.py": "1c3ef968ac9a868dce24edb47abda2462367d8945dcc95402b5d7431963c831b"
}

_SHA = re.compile(r"[0-9a-f]{64}\Z")


class M04BSuccessorError(ValueError):
    """No provider/source text is ever included in these validation errors."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal(path: Path, name: str):
    try:
        syntax = ast.parse(path.read_text(encoding="utf-8"))
        nodes = [node.value for node in syntax.body
                 if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == name
                         for target in node.targets)]
        if len(nodes) != 1:
            raise ValueError("assignment")
        return ast.literal_eval(nodes[0])
    except (OSError, SyntaxError, ValueError, TypeError, RecursionError):
        raise M04BSuccessorError("invalid_revision_assignment") from None


def _schema_tables(path: Path) -> frozenset[str]:
    try:
        syntax = ast.parse(path.read_text(encoding="utf-8"))
        found = []
        for node in ast.walk(syntax):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "op"
                    and node.func.attr == "create_table"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                found.append(node.args[0].value)
        return frozenset(found)
    except (OSError, SyntaxError, TypeError, ValueError):
        raise M04BSuccessorError("invalid_migration") from None


def _manifest_path(root: Path) -> Path:
    return root / MANIFEST_PATH


def successor_exists(root: Path) -> bool:
    return _manifest_path(root).is_file()


def validate_successor(root: Path) -> dict:
    """Independently validate the 0024 successor without importing old guards.

    This is deliberately nonrecursive so chained historical package checks can
    use it for exact verified SHA transitions.
    """
    if not successor_exists(root):
        raise M04BSuccessorError("successor_evidence_missing")
    try:
        obj = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
        metadata = {
            "package": "AI004-M04B-SCHEMA-SUCCESSOR",
            "source_commit": SOURCE_COMMIT,
            "source_tree": SOURCE_TREE,
            "schema_from": SCHEMA_FROM,
            "schema_to": SCHEMA_TO,
            "legal_state": "DRAFT",
            "public_real_data_enabled": False,
            "provider_calls": 0,
            "production_migration": "NOT_RUN",
            "deployment": "NOT_RUN",
            "scope": "draft-disposable-ci-only",
        }
        if (not isinstance(obj, dict)
                or set(obj) != set(metadata) | {
                    "reviewed_runtime_changes", "new_runtime_sha256",
                    "preserved_sha256",
                } or any(type(obj.get(k)) is not type(v) or obj[k] != v
                         for k, v in metadata.items())):
            raise M04BSuccessorError("invalid_metadata")
        rows = obj["reviewed_runtime_changes"]
        new = obj["new_runtime_sha256"]
        preserved = obj["preserved_sha256"]
        if (not isinstance(rows, dict) or set(rows) != set(PREDECESSOR_HASHES)
                or not isinstance(new, dict) or set(new) != NEW_FILES
                or not isinstance(preserved, dict) or set(preserved) != PRESERVED_FILES):
            raise M04BSuccessorError("invalid_scope")
        if set(PRESERVED_SHA256) != PRESERVED_FILES:
            raise M04BSuccessorError("invalid_preservation_lock")
        for relative, pair in rows.items():
            if (not isinstance(pair, dict)
                    or set(pair) != {"previous_sha256", "current_sha256"}
                    or pair["previous_sha256"] != PREDECESSOR_HASHES[relative]
                    or not isinstance(pair["current_sha256"], str)
                    or not _SHA.fullmatch(pair["current_sha256"])
                    or _digest(root / relative) != pair["current_sha256"]):
                raise M04BSuccessorError("successor_hash_mismatch")
        for relative, expected in new.items():
            if (not isinstance(expected, str) or not _SHA.fullmatch(expected)
                    or _digest(root / relative) != expected):
                raise M04BSuccessorError("successor_new_file_mismatch")
        for relative, expected in preserved.items():
            if (expected != PRESERVED_SHA256[relative]
                    or _digest(root / relative) != expected):
                raise M04BSuccessorError("historical_evidence_changed:" + relative)
        if (_literal(root / MIGRATION, "revision") != SCHEMA_TO
                or _literal(root / MIGRATION, "down_revision") != SCHEMA_FROM
                or _schema_tables(root / MIGRATION) != MATCHING_TABLES
                or _literal(root / "database.py", "CURRENT_REVISION") != SCHEMA_TO):
            raise M04BSuccessorError("invalid_schema_transition")
        if "REAL_DATA_SUPPORTED = False" not in (root / "domain/ai.py").read_text():
            raise M04BSuccessorError("real_data_activated")
        if 'release_state="DRAFT"' not in (root / "services/legal_policy.py").read_text():
            raise M04BSuccessorError("legal_state_activated")
        return obj
    except (M04BSuccessorError,):
        raise
    except (OSError, KeyError, UnicodeError, TypeError, ValueError,
            json.JSONDecodeError):
        raise M04BSuccessorError("invalid_successor_evidence") from None


def expected_schema_head(root: Path, historical_head: str) -> str:
    if not successor_exists(root):
        return historical_head
    validate_successor(root)
    if historical_head != SCHEMA_FROM:
        raise M04BSuccessorError("invalid_predecessor_schema")
    return SCHEMA_TO


def approved_sha256(root: Path, relative: str, historical_sha256: str) -> str:
    """Only a proven 0023 main SHA may advance to its exact 0024 successor."""
    if not successor_exists(root):
        return historical_sha256
    data = validate_successor(root)
    row = data["reviewed_runtime_changes"].get(relative)
    if row is None:
        return historical_sha256
    if historical_sha256 != row["previous_sha256"]:
        raise M04BSuccessorError("invalid_successor_predecessor")
    return row["current_sha256"]


def revision_is_authorized(root: Path, *, predecessor: str = SCHEMA_FROM) -> bool:
    """Useful for migration chronology tests, never a silent bool bypass."""
    return expected_schema_head(root, predecessor) == SCHEMA_TO
