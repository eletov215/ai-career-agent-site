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
from scripts.legal001_canonical import validate_versions

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
    """Validate current release metadata and preserve accepted historical scopes."""
    errors: list[str] = validate_versions(plan, passport)
    complete = "ВЫПОЛНЕНО"
    deferred = "ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА"
    status = "**Статус:**"
    card = re.search(r"^#### AI-PROVIDER-001[^\n]*\n(.*?)(?=^#### |\Z)", plan, re.M | re.S)
    if card is None or status + " " + complete not in card.group(1):
        errors.append("AI-PROVIDER-001 card must be complete after final CI")
    roadmap = next((line for line in plan.splitlines() if line.startswith("| AI-PROVIDER-001 |")), "")
    if complete not in roadmap:
        errors.append("AI-PROVIDER-001 roadmap must be complete")
    legal_rows = [line for line in plan.splitlines() if line.startswith("| LEGAL-001 | P0")]
    if not legal_rows or any(deferred not in line for line in legal_rows):
        errors.append("LEGAL-001 must preserve the recorded owner deferral")
    for label, text in (("plan", plan), ("passport", passport)):
        head = text.split('<!-- ACA-CANONICAL-STATUS:START -->', 1)[-1].split('<!-- ACA-CANONICAL-STATUS:END -->', 1)[0]
        current = next((line for line in head.splitlines() if line.startswith("| Current full package |")), "")
        previous = next((line for line in head.splitlines() if line.startswith("| Accepted predecessor |")), "")
        accepted = next((line for line in head.splitlines() if line.startswith("| Accepted foundation |")), "")
        if not all(value in current for value in ("AI-005", "IN_PROGRESS")):
            errors.append(label + " AI-005 full scope must remain in progress")
        if not all(value in previous for value in ("JOB-001", "COMPLETE", "1.6.1", "2.76")):
            errors.append(label + " accepted predecessor is inconsistent")
        if "AI-004 COMPLETE" not in accepted or "synthetic/reference-only" not in accepted:
            errors.append(label + " accepted AI-004 foundation is inconsistent")
    job_card = re.search(r"^#### JOB-001[^\n]*\n(.*?)(?=^#### |\Z)", plan, re.M | re.S)
    job_row = next((line for line in plan.splitlines() if line.startswith("| JOB-001 |")), "")
    if job_card is None or status + " " + complete not in job_card.group(1) or complete not in job_row:
        errors.append("JOB-001 must retain the accepted functional status")
    match_card = re.search(r"^#### AI-004[^\n]*\n(.*?)(?=^#### |\Z)", plan, re.M | re.S)
    if match_card is None or status + " " + complete not in match_card.group(1):
        errors.append("AI-004 card must preserve the accepted reference scope")
    match_row = next((line for line in plan.splitlines() if line.startswith("| AI-004 |")), "")
    if complete not in match_row:
        errors.append("AI-004 roadmap must be complete")
    doc = re.search(r"^#### DOC-001[^\n]*\n(.*?)(?=^#{1,4} |\Z)", plan, re.M | re.S)
    # Preserve the dated pre-LEGAL checkpoint inside the retained plan body.
    # Current release versions are checked separately above, from the first
    # metadata table, not by finding old version strings in the history.
    inventory = next((line for line in (doc.group(1) if doc else "").splitlines()
                      if line.startswith("**Current state:**")), "")
    if not all(v in inventory for v in ("PLAN_CURRENT 1.6.3;", "PROJECT_PASSPORT 2.78;", "SOURCE_AUDIT 1.6.3", "20260917_0020", "CI285 attempt2", "r2 NEEDS_VERIFICATION", "AI-005 IN_PROGRESS / LIVE_NOT_ACCEPTED")):
        errors.append("Historical DOC-001 checkpoint is inconsistent")
    return errors


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        policy = load_policy(root / "docs/policies/ai_provider_policy.v1.json")
        evidence_dir = root / "docs/evidence/ai-provider-001"
        preserved = json.loads((evidence_dir / "preserved_files_sha256.json").read_text(encoding="utf-8"))
        from scripts.check_ai001_package import load_boundary
        successor = load_boundary(root)
        if (root / "docs/evidence/legal-001/change_boundary.json").is_file():
            from scripts.legal001_boundary import successor_hashes
            successor = {
                **successor,
                **{relative: {"current_sha256": sha} for relative, sha in successor_hashes(root).items()},
            }
        for relative, expected in preserved["files"].items():
            if relative in successor:
                expected = successor[relative]["current_sha256"]
            path = root / relative
            if not path.is_file():
                errors.append(f"preserved file missing: {relative}")
                continue
            data = path.read_bytes()
            actual = hashlib.sha256(data).hexdigest()
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
        if {row["id"] for row in sources["sources"]} != {f"S{i}" for i in range(1, 11)}:
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
        from scripts.check_job001_package import validate_closure
        errors.extend(validate_closure(root))
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
    print(json.dumps({"ok": not errors, "package": "AI-PROVIDER-001", "scope": "offline only",
                      "owner_approval": "approved", "external_ci": "not_attested_by_local_check", "errors": errors}, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
