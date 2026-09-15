#!/usr/bin/env python3
"""Check the AI-PROVIDER-001 candidate without any external service or credential."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.ai_provider_policy import PolicyError, cost_report, load_policy

DOCUMENTS = (
    "AI_PROVIDER001_DECISION", "AI_PROVIDER001_DATA_AND_FAILURE_POLICY",
    "AI_PROVIDER001_COSTS", "AI_PROVIDER001_SOURCES", "AI_PROVIDER001_VERIFICATION_STATUS",
)
HARD_COUNTERS = (
    "unsupported_number_count", "unsupported_impact_claim_count", "forbidden_claim_count",
    "cover_letter_presentation_violation_count", "user_facing_technical_token_count",
    "scenario_provenance_violation_count", "claim_evidence_violation_count",
)


def validate_canonical_status(plan: str, passport: str) -> list[str]:
    """Reject status drift after the provider package is formally closed."""
    errors: list[str] = []
    complete = "ВЫПОЛНЕНО"
    ready = "НУЖНА ПРОВЕРКА"
    deferred = "ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА"
    status = "**Статус:**"
    card = re.search(r"^#### AI-PROVIDER-001[^\n]*\n(.*?)(?=^#### |\Z)", plan, re.M | re.S)
    if card is None or status + " " + complete not in card.group(1):
        errors.append("AI-PROVIDER-001 card must be complete after final CI")
    roadmap = next((line for line in plan.splitlines() if line.startswith("| AI-PROVIDER-001 |")), "")
    if complete not in roadmap:
        errors.append("AI-PROVIDER-001 roadmap must be complete")
    legal_rows = [line for line in plan.splitlines() if line.startswith("| LEGAL-001 | P0") ]
    if not legal_rows or any(deferred not in line for line in legal_rows):
        errors.append("LEGAL-001 must preserve the recorded owner deferral")
    for label, text in (("plan", plan), ("passport", passport)):
        current = next((line for line in text.splitlines() if line.startswith("| Current package |")), "")
        if "AI-002" not in current or ready not in current:
            errors.append(label + " active package is inconsistent")
    doc = re.search(r"^#### DOC-001[^\n]*\n(.*?)(?=^### |\Z)", plan, re.M | re.S)
    if doc is None or not all(v in doc.group(1) for v in ("1.5.2", "2.69", "20260914_0015", complete, ready, deferred)):
        errors.append("DOC-001 active version inventory is stale")
    return errors


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        policy = load_policy(root / "docs/policies/ai_provider_policy.v1.json")
        evidence_dir = root / "docs/evidence/ai-provider-001"
        preserved = json.loads((evidence_dir / "preserved_files_sha256.json").read_text(encoding="utf-8"))
        from scripts.check_ai001_package import load_boundary
        successor = load_boundary(root)
        for relative, expected in preserved["files"].items():
            if relative in successor:
                expected = successor[relative]["current_sha256"]
            path = root / relative
            if not path.is_file():
                errors.append(f"preserved file missing: {relative}")
                continue
            data = path.read_bytes()
            actual = hashlib.sha256(data).hexdigest()
            # Git autocrlf is not an architectural change. The source ZIP audit
            # separately uses exact byte comparisons when packaging releases.
            normalized = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
            if actual != expected and normalized != expected:
                errors.append(f"preserved application/benchmark boundary changed: {relative}")
        if (root / "routes/ai.py").exists():
            errors.append("No unreviewed public AI generation route is allowed")
        summary = json.loads((root / "docs/evidence/ai-bench-001/alice-final-run-7-summary.json").read_text(encoding="utf-8"))
        s = summary["summary"]
        if s["case_count"] != 8 or s["passed_count"] != 8 or s["error_count"] or s["retry_count"]:
            errors.append("accepted final benchmark summary is inconsistent")
        if any(s.get(counter) != 0 for counter in HARD_COUNTERS):
            errors.append("accepted benchmark has non-zero or missing hard counters")
        if summary["review"]["status"] != "PASS" or summary["review"]["numeric_scores"] is not None:
            errors.append("qualitative human acceptance must not invent numeric scores")
        if summary["dataset"]["version"] != policy["primary"]["qualification_dataset"]:
            errors.append("provider decision and accepted dataset differ")
        actual_cost = cost_report(policy, summary)
        saved_cost = json.loads((evidence_dir / "cost_snapshot.json").read_text(encoding="utf-8"))
        if saved_cost != actual_cost:
            errors.append("cost snapshot is not reproducible from checked prices and usage")
        sources = json.loads((evidence_dir / "research_sources.json").read_text(encoding="utf-8"))
        if {row["id"] for row in sources["sources"]} != {f"S{i}" for i in range(1,11)}:
            errors.append("source register is incomplete")
        if sources["checked_on"] != policy["checked_on"]:
            errors.append("source register and policy check dates differ")
        for name in DOCUMENTS:
            text = (root / "docs" / f"{name}.md").read_text(encoding="utf-8")
            if not all(marker in text for marker in ("# AI Career Agent", "AI-PROVIDER-001", "20260819_0014", "## 1.", "## 2.")):
                errors.append(f"provider document is incomplete: {name}")
        plan = (root / "docs/PLAN_CURRENT.md").read_text(encoding="utf-8")
        passport = (root / "docs/PROJECT_PASSPORT.md").read_text(encoding="utf-8")
        errors.extend(validate_canonical_status(plan, passport))
        if "1.5.2" not in plan or "2.69" not in passport:
            errors.append("current canonical versions are not synchronized")
        workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        if "python scripts/check_ai_provider_package.py" not in workflow:
            errors.append("ordinary CI must check the provider decision package")
        if "test_ai_provider*.py" not in workflow:
            errors.append("ordinary CI must run the provider negative tests")
    except PolicyError as exc:
        errors.append(str(exc))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        errors.append("required package evidence is missing or malformed")
    return errors


def main() -> int:
    errors = validate()
    print(json.dumps({"ok":not errors,"package":"AI-PROVIDER-001","scope":"offline only",
                      "owner_approval":"approved","external_ci":"not_attested_by_local_check","errors":errors},ensure_ascii=False,indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
