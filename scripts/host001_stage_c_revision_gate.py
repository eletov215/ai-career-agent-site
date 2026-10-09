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

    return {
        "revision": heads[0],
        "migration_count": len(entries),
        "unique_head": True,
        "fixture_uses_runtime_revision": True,
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
