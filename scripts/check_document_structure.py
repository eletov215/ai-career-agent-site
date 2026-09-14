#!/usr/bin/env python3
"""Enforce the unified project document template (DOC-STD-001)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS = {
    "docs/AI_PROVIDER001_DECISION.md": ["| \u041f\u043e\u043b\u0435 | \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435 |", "## 1.", "## 2."],
    "docs/AI_PROVIDER001_DATA_AND_FAILURE_POLICY.md": ["| \u041f\u043e\u043b\u0435 | \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435 |", "## 1.", "## 2."],
    "docs/AI_PROVIDER001_COSTS.md": ["| \u041f\u043e\u043b\u0435 | \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435 |", "## 1.", "## 2."],
    "docs/AI_PROVIDER001_SOURCES.md": ["| \u041f\u043e\u043b\u0435 | \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435 |", "## 1.", "## 2."],
    "docs/AI_PROVIDER001_VERIFICATION_STATUS.md": ["| \u041f\u043e\u043b\u0435 | \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435 |", "## 1.", "## 2."],
    "README.md": ["## 1.", "## 2.", "INFRA-001"],
    "docs/PLAN_CURRENT.md": ["| Поле | Значение |", "## 1.", "INFRA-001", "OPS-001"],
    "docs/PROJECT_PASSPORT.md": ["| Поле | Значение |", "## 1.", "INFRA-001"],
    "docs/DOCUMENT_STANDARD.md": ["DOC-STD-001", "## 1."],
    "docs/INFRA001_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/INFRA001_VPS_TEST.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/INFRA001_PROVIDER_DECISION.md": ["| Поле | Значение |", "## 1."],
    "docs/INFRA001_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1."],
    "docs/OPS001_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1."],
    "docs/SYNC001_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SYNC001_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SYNC001_VERIFICATION_STATUS.md": [
        "| Поле | Значение |",
        "## 1.",
        "## 2.",
    ],
    "docs/SYNC002_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SYNC002_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SYNC002_VERIFICATION_STATUS.md": [
        "| Поле | Значение |",
        "## 1.",
        "## 2.",
    ],
    "docs/SEARCH001_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH001_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH001_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH001_CONTRACT_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH002_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH002_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH002_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH002_DEDUP_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH003_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH003_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH003_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/SEARCH003_PAGINATION_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH001_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH001_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH001_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH001_SECURITY_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH002_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH002_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH002_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AUTH002_SECURITY_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF001_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF001_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF001_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF001_PROFILE_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF002_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF002_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF002_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF002_EXTRACTION_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF002_SECURITY_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF003_IMPLEMENTATION.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF003_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF003_RUNBOOK.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF003_RESUME_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/PROF003_SECURITY_REFERENCE.md": ["| Поле | Значение |", "## 1.", "## 2."],
    "docs/AI_BENCH_VERIFICATION_STATUS.md": ["| Поле | Значение |", "## 1."],
    "docs/SOURCE_AUDIT.md": ["| Поле | Значение |", "## 1."],
}


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative, markers in DOCUMENTS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing document: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("# "):
            errors.append(f"{relative}: first line must be an H1 title")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative}: missing required marker {marker!r}")
        headings = re.findall(r"^##\s+(.+)$", text, flags=re.MULTILINE)
        if relative != "README.md" and not any(re.match(r"\d+\.\s", heading) for heading in headings):
            errors.append(f"{relative}: level-2 sections must be numbered")
        if "\t" in text:
            errors.append(f"{relative}: literal tab characters are forbidden; use Markdown structure")
    return errors


def main() -> int:
    errors = validate(ROOT)
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
