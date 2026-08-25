"""Fail CI when generated, secret, or local-runtime files are committed."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

FORBIDDEN_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
}
FORBIDDEN_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "app.db",
}
FORBIDDEN_ROOT_FILE_NAMES = {
    "CHANGED_FILES.txt",
    "DELETE_FILES.txt",
    "LOCAL_VERIFICATION_REPORT.txt",
    "PATCH_INFO.json",
    "PATCH_MANIFEST.txt",
    "README_FIRST.txt",
    "README_UPLOAD.txt",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pem",
    ".key",
    ".p12",
    ".sqlite",
    ".sqlite3",
    ".dump",
    ".backup",
    ".sql",
    ".enc",
}


def _tracked_paths(root: Path) -> list[Path] | None:
    """Return tracked files in Git, or None when the directory is not a checkout."""
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def _filesystem_paths(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file()]


def find_violations(root: Path) -> list[str]:
    root = root.resolve()
    paths = _tracked_paths(root) or _filesystem_paths(root)
    violations: set[str] = set()

    for path in paths:
        try:
            relative = path.resolve().relative_to(root)
        except (OSError, ValueError):
            continue

        parts = relative.parts
        if any(part in FORBIDDEN_DIR_NAMES for part in parts[:-1]):
            violations.add(str(relative))
            continue

        name = relative.name
        lower_name = name.lower()
        if len(parts) == 1 and name in FORBIDDEN_ROOT_FILE_NAMES:
            violations.add(str(relative))
            continue
        if name in FORBIDDEN_FILE_NAMES or lower_name.startswith(".env."):
            if name != ".env.example":
                violations.add(str(relative))
                continue
        if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.add(str(relative))
            continue

        if len(parts) >= 3 and parts[0] == "evals" and parts[1] == "artifacts":
            if relative.as_posix() != "evals/artifacts/README.md":
                violations.add(str(relative))

    return sorted(violations)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"Repository root does not exist: {root}", file=sys.stderr)
        return 2

    violations = find_violations(root)
    if violations:
        print("Repository hygiene check failed. Remove these files:", file=sys.stderr)
        for item in violations:
            print(f" - {item}", file=sys.stderr)
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
