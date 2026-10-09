#!/usr/bin/env python3
"""Offline, read-only Alembic/checkout preflight for HOST-001 Stage C.

Checks repository files and the selected Git commit only. It does not connect
to PostgreSQL, Terraform, Yandex Cloud, Render, or Neon; it cannot migrate data.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION_PATTERN = re.compile(r"[0-9]{8}_[0-9]{4}")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
# Optional AI004-M04B schema must not silently bypass the Stage C backup/restore schema digest.
MATCHING_TABLES = frozenset({"user_match_reports", "user_match_cache"})


class StageCRevisionGateError(RuntimeError):
    pass


def _static_assignment(path: Path, variable: str) -> object:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    except (OSError, SyntaxError) as exc:
        raise StageCRevisionGateError(
            f"Cannot inspect {path.name} safely as Python source."
        ) from exc

    values: list[object] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            ]
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value_node = node.value
        else:
            continue
        if variable not in names:
            continue
        try:
            values.append(ast.literal_eval(value_node))
        except (ValueError, TypeError, SyntaxError, RecursionError) as exc:
            raise StageCRevisionGateError(
                f"{path.name}: {variable} must be a static literal."
            ) from exc
    if len(values) != 1:
        raise StageCRevisionGateError(
            f"{path.name}: expected exactly one {variable} assignment."
        )
    return values[0]



def _created_matching_tables(migrations_dir: Path) -> frozenset[str]:
    """Discover M04B creation by AST without executing migration code."""
    found: set[str] = set()
    for path in sorted(migrations_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            syntax = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        except (OSError, SyntaxError) as exc:
            raise StageCRevisionGateError(
                f"Cannot inspect matching tables in migration {path.name}."
            ) from exc
        for node in ast.walk(syntax):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "create_table"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "op"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                continue
            if node.args[0].value in MATCHING_TABLES:
                found.add(node.args[0].value)
    return frozenset(found)


def _stage_c_schema_digest_tables(fixture: Path) -> frozenset[str]:
    """Read the fixture's explicitly reviewed table list, never import it."""
    try:
        syntax = ast.parse(fixture.read_text(encoding="utf-8"), filename=fixture.name)
    except (OSError, SyntaxError) as exc:
        raise StageCRevisionGateError("Cannot inspect the Stage C fixture schema list.") from exc
    functions = [
        node for node in syntax.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_schema_report"
    ]
    if len(functions) != 1:
        raise StageCRevisionGateError("Stage C must define exactly one _schema_report.")
    found: list[object] = []
    for node in ast.walk(functions[0]):
        if not (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "selected_tables"
                for target in node.targets
            )
        ):
            continue
        try:
            found.append(ast.literal_eval(node.value))
        except (ValueError, TypeError, SyntaxError, RecursionError) as exc:
            raise StageCRevisionGateError(
                "Stage C schema digest table allowlist must remain a static literal."
            ) from exc
    if len(found) != 1 or not isinstance(found[0], (tuple, list)):
        raise StageCRevisionGateError(
            "Stage C must have one static selected_tables schema digest list."
        )
    tables = found[0]
    if any(not isinstance(table, str) for table in tables):
        raise StageCRevisionGateError("Stage C schema digest tables must be strings.")
    return frozenset(tables)


def _check_matching_schema_coverage(root: Path, migrations_dir: Path) -> str:
    """Require new M04B tables in backup inventory and restore schema digest."""
    created = _created_matching_tables(migrations_dir)
    if not created:
        return "NOT_PRESENT"
    if created != MATCHING_TABLES:
        raise StageCRevisionGateError(
            "Partial AI004-M04B matching migration is not safe for Stage C."
        )
    inventory = _static_assignment(root / "operations" / "backup.py", "_INVENTORY_TABLES")
    if not isinstance(inventory, (tuple, list)) or not MATCHING_TABLES.issubset(
        set(inventory)
    ):
        raise StageCRevisionGateError(
            "Stage C requires both M04B tables in the encrypted backup inventory."
        )
    selected = _stage_c_schema_digest_tables(
        root / "scripts" / "host001_stage_c_fixture.py"
    )
    if not MATCHING_TABLES.issubset(selected):
        raise StageCRevisionGateError(
            "Stage C schema digest omits M04B matching tables; review synthetic restore coverage."
        )
    # Schema/inventory coverage is NOT evidence of populated matching-row restore.
    return "SCHEMA_INVENTORY_ONLY"


def check_revision_chain(root: Path = ROOT) -> dict[str, object]:
    """Reject branches, orphan migrations, cycles, or stale CURRENT_REVISION."""
    migrations_dir = root / "migrations" / "versions"
    if not migrations_dir.is_dir():
        raise StageCRevisionGateError("Migration versions directory is missing.")

    entries: dict[str, str | None] = {}
    for path in sorted(migrations_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        revision = _static_assignment(path, "revision")
        parent = _static_assignment(path, "down_revision")
        if not isinstance(revision, str) or not REVISION_PATTERN.fullmatch(revision):
            raise StageCRevisionGateError("Migration revision format is invalid.")
        if not path.name.startswith(revision + "_"):
            raise StageCRevisionGateError(
                f"Migration filename does not match its revision: {path.name}."
            )
        if parent is not None and (
            not isinstance(parent, str) or not REVISION_PATTERN.fullmatch(parent)
        ):
            raise StageCRevisionGateError(
                f"{path.name}: down_revision must be one simple revision or None."
            )
        if revision in entries:
            raise StageCRevisionGateError("Duplicate Alembic revision found.")
        entries[revision] = parent

    if not entries:
        raise StageCRevisionGateError("No Alembic revisions found.")
    roots = [revision for revision, parent in entries.items() if parent is None]
    if len(roots) != 1:
        raise StageCRevisionGateError("Expected exactly one migration root.")
    if any(parent is not None and parent not in entries for parent in entries.values()):
        raise StageCRevisionGateError("Migration chain has a missing parent.")

    referenced = {parent for parent in entries.values() if parent is not None}
    heads = [revision for revision in entries if revision not in referenced]
    if len(heads) != 1:
        raise StageCRevisionGateError(
            "Expected one Alembic head; merge or resolve migration branches."
        )
    visited: set[str] = set()
    current: str | None = heads[0]
    while current is not None:
        if current in visited:
            raise StageCRevisionGateError("Cycle found in the migration chain.")
        visited.add(current)
        current = entries[current]
    if len(visited) != len(entries):
        raise StageCRevisionGateError("Migration chain contains disconnected nodes.")

    runtime_revision = _static_assignment(root / "database.py", "CURRENT_REVISION")
    if runtime_revision != heads[0]:
        raise StageCRevisionGateError(
            "Runtime CURRENT_REVISION differs from the unique Alembic head."
        )

    fixture = root / "scripts" / "host001_stage_c_fixture.py"
    try:
        fixture_text = fixture.read_text(encoding="utf-8")
    except OSError as exc:
        raise StageCRevisionGateError("Stage C synthetic fixture is missing.") from exc
    if "from database import CURRENT_REVISION" not in fixture_text:
        raise StageCRevisionGateError(
            "Stage C synthetic fixture must use the runtime revision dynamically."
        )

    matching_schema_coverage = _check_matching_schema_coverage(root, migrations_dir)

    return {
        "revision": heads[0],
        "migration_count": len(entries),
        "unique_head": True,
        "fixture_uses_runtime_revision": True,
        "matching_schema_coverage": matching_schema_coverage,
    }


def check_checkout_sha(root: Path, expected_sha: str) -> str:
    """Pin the offline preflight to the precise, reviewed source commit."""
    if not COMMIT_PATTERN.fullmatch(expected_sha):
        raise StageCRevisionGateError("Expected SHA must be a full 40-character Git SHA.")
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise StageCRevisionGateError("Unable to identify the local Git commit.") from exc
    checkout_sha = completed.stdout.strip()
    if checkout_sha != expected_sha:
        raise StageCRevisionGateError(
            "Checkout differs from the explicitly reviewed commit; stop before Stage C."
        )
    return checkout_sha


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-sha",
        required=True,
        help="Exact 40-character commit SHA reviewed for the planned Stage C run.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="Repository checkout containing migrations/versions and database.py.",
    )
    args = parser.parse_args()
    try:
        snapshot = check_revision_chain(args.repo_root)
        sha = check_checkout_sha(args.repo_root, args.expected_sha)
    except StageCRevisionGateError as exc:
        print(json.dumps({
            "package": "HOST-001",
            "scope": "offline-revision-gate",
            "ok": False,
            "reason": str(exc),
            "cloud_calls": 0,
            "database_changes": 0,
        }, ensure_ascii=False))
        return 1
    print(json.dumps({
        "package": "HOST-001",
        "scope": "offline-revision-gate",
        "ok": True,
        "source_commit": sha,
        **snapshot,
        "cloud_calls": 0,
        "database_changes": 0,
        "authorizes_paid_apply": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
