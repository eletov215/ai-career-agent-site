"""Dependency-free structural check for the CODEX-OPS-001 workflow package."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "issue-delivery": ("GitHub issue", "BLOCKED_GITHUB_ACCESS", "main"),
    "package-guard-verification": ("historical", "python -S -m unittest"),
    "safety-boundaries": (
        "REAL_DATA_SUPPORTED = False",
        "DRAFT",
        "billable Alice/Yandex",
        "AI-006",
    ),
}


def validate(root: Path = ROOT) -> list[str]:
    """Return human-readable violations without importing application code."""
    errors: list[str] = []
    guide = root / "AGENTS.md"
    if not guide.is_file():
        errors.append("AGENTS.md is missing")
    else:
        source = guide.read_text(encoding="utf-8")
        for skill in SKILLS:
            if f"`{skill}`" not in source:
                errors.append(f"AGENTS.md does not route to {skill}")

    for name, markers in SKILLS.items():
        path = root / ".agents" / "skills" / name / "SKILL.md"
        if not path.is_file():
            errors.append(f"missing repo skill: {name}")
            continue
        source = path.read_text(encoding="utf-8")
        if not source.startswith("---\n"):
            errors.append(f"{name} has no YAML front matter")
        if f"name: {name}" not in source or "description:" not in source:
            errors.append(f"{name} has invalid skill metadata")
        for marker in markers:
            if marker not in source:
                errors.append(f"{name} is missing required boundary: {marker}")

    if "REAL_DATA_SUPPORTED = False" not in (
        root / "domain" / "ai.py"
    ).read_text(encoding="utf-8"):
        errors.append("real-data AI boundary changed")
    legal = (root / "services" / "legal_policy.py").read_text(encoding="utf-8")
    if 'release_state="DRAFT"' not in legal:
        errors.append("production legal policy is not DRAFT")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("CODEX-OPS-001 repository workflow: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
