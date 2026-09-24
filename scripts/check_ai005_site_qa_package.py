#!/usr/bin/env python3
"""Dependency-light AI-005 synthetic SITE QA package guard."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "routes/ai005_site_qa.py",
    "services/ai/letter_site_qa.py",
    "templates/letters/site_qa_review.html",
    "templates/letters/site_qa_index.html",
    "templates/letters/site_qa_preview.html",
    "templates/letters/site_qa_detail.html",
    "templates/letters/site_qa_version.html",
    "templates/letters/site_qa_error.html",
    "tests/test_ai005_site_qa.py",
    "docs/evidence/ai-005-site-qa/change_boundary.json",
    "scripts/ai005_site_qa_boundary.py",
}


def validate(root: Path = ROOT) -> list[str]:
    errors = []
    try:
        from scripts.ai005_site_qa_boundary import verify_successor
        verify_successor(root)
        for rel in REQUIRED:
            if not (root / rel).is_file():
                errors.append("Missing SITE QA file: " + rel)
        if errors:
            return errors

        app = (root / "app.py").read_text()
        if "create_ai005_site_qa_blueprint" not in app or "AliceLetterSiteQA" not in app:
            errors.append("SITE QA is not registered")
        if "REAL_DATA_SUPPORTED = False" not in (root / "domain/ai.py").read_text():
            errors.append("Real-data Alice was enabled")
        if 'release_state="DRAFT"' not in (root / "services/legal_policy.py").read_text():
            errors.append("Legal policy was activated")

        service = (root / "services/ai/letter_site_qa.py").read_text()
        for marker in (
            "SyntheticLetterAdmission",
            "synthetic_cases()",
            "uuid5(",
            'email=None',
            'normalized_email=None',
            'password_hash=None',
            'confirmed=True',
            'SITE_QA_FACT_ID = "profile.summary"',
        ):
            if marker not in service:
                errors.append("SITE QA isolation control missing: " + marker)
        if "os.environ" in service or "request.form" in service:
            errors.append("SITE QA service must not select synthetic admission from environment/client payload")

        route = (root / "routes/ai005_site_qa.py").read_text()
        for marker in ("is_search_admin", "_REVIEW_SESSION_KEY", 'fields({"language", "length", "tone"})',
                       'fields({"review_token"})', 'confirmed=data["confirm"] == "1"'):
            if marker not in route:
                errors.append("SITE QA route control missing: " + marker)
        if "candidate_text" in route or "vacancy_text" in route or "source_json" in route:
            errors.append("SITE QA route accepts arbitrary source data")

        preview = (root / "templates/letters/site_qa_preview.html").read_text()
        if "Создать черновик с Алисой" not in preview or 'name="review_token"' not in preview:
            errors.append("SITE QA generate action is missing")
        if 'name="confirm"' in preview:
            errors.append("Redundant per-call confirmation checkbox returned")
        if "|safe" in preview:
            errors.append("SITE QA preview bypasses template escaping")

        for rel in ("routes/ai005_site_qa.py", "services/ai/letter_site_qa.py", "tests/test_ai005_site_qa.py"):
            ast.parse((root / rel).read_text())

        workflow = (root / ".github/workflows/ci.yml").read_text()
        if "check_ai005_site_qa_package.py" not in workflow or "test_ai005_site_qa.py" not in workflow:
            errors.append("Dedicated SITE QA CI gate missing")
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        errors.append("Invalid AI-005 SITE QA package: " + type(exc).__name__)
    return errors


if __name__ == "__main__":
    problems = validate()
    print(json.dumps({
        "package": "AI-005",
        "tranche": "site-qa-synthetic",
        "ok": not problems,
        "billable_calls": 0,
        "real_data_enabled": False,
        "errors": problems,
    }, ensure_ascii=False, indent=2))
    raise SystemExit(bool(problems))
