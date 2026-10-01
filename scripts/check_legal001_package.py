#!/usr/bin/env python3
"""Dependency-free LEGAL-001 consent/admission package guard."""
from pathlib import Path
import ast
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.legal001_boundary import successor_hashes
from scripts.legal001_canonical import validate as validate_canonical

REQUIRED={
    "domain/consent.py","models/consent.py","repositories/consent.py","services/consent.py",
    "services/legal_policy.py","services/ai/letter_admission.py",
    "routes/privacy_controls.py","templates/privacy/ai_consent.html",
    "migrations/versions/20260922_0021_legal_consent.py",
    "tests/test_legal001_migration.py","tests/test_legal001_service.py",
    "tests/test_legal001_routes.py","tests/test_legal001_admission.py",
    "tests/test_legal001_postgresql.py",".github/workflows/legal001-postgresql.yml",
    "tests/test_legal001_canonical.py","scripts/legal001_canonical.py",
    "tests/test_legal001_binding.py","docs/LEGAL001_SOURCE_REVIEW.md",
    "docs/LEGAL001_SCOPE.md","docs/LEGAL001_IMPLEMENTATION.md",
    "docs/LEGAL001_RUNBOOK.md","docs/LEGAL001_VERIFICATION_STATUS.md",
    "docs/evidence/legal-001/ci304_verified_summary.json",
    "docs/evidence/legal-001/ci324_verified_summary.json",
    "docs/evidence/legal-001/technical_acceptance_20260924.json",
}

def validate(root=ROOT):
    errors=[]
    try:
        successor_hashes(root)
        for rel in REQUIRED:
            if not (root/rel).is_file(): errors.append("Missing: "+rel)
        expected_head = "20261001_0022" if (root/"docs/evidence/job-002/change_boundary.json").is_file() else "20260922_0021"
        if f'CURRENT_REVISION = "{expected_head}"' not in (root/"database.py").read_text():
            errors.append("Unexpected schema head")
        migration=(root/"migrations/versions/20260922_0021_legal_consent.py").read_text()
        tree=ast.parse(migration)
        tables={n.args[0].value for n in ast.walk(tree)
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                and n.func.attr=="create_table" and n.args and isinstance(n.args[0],ast.Constant)}
        if tables!={"ai_consents"} or 'down_revision = "20260917_0020"' not in migration:
            errors.append("Invalid additive consent migration")
        policy=(root/"services/legal_policy.py").read_text()
        if 'release_state="DRAFT"' not in policy or "PLACEHOLDER REQUIRED" not in policy:
            errors.append("Production legal policy must remain DRAFT")
        if any(token in policy for token in ("os.environ","getenv(","AI_LEGAL_APPROVED")):
            errors.append("Legal policy cannot be environment-activated")
        domain=(root/"domain/ai.py").read_text()
        if "REAL_DATA_SUPPORTED = False" not in domain:
            errors.append("Real-data product boundary changed")
        admission=(root/"services/ai/letter_admission.py").read_text()
        for marker in ("LegalLetterAdmission","require_current_acceptance","policy.production_active",
                       "REAL_DATA_SUPPORTED","generation_unavailable"):
            if marker not in admission: errors.append("Missing admission control: "+marker)
        if any(token in admission for token in ("os.environ","getenv(","AI_LEGAL_APPROVED")):
            errors.append("Admission cannot be environment-activated")
        app=(root/"app.py").read_text()
        if "admission=LegalLetterAdmission(CONSENT_SERVICE)" not in app:
            errors.append("Application did not install LEGAL-001 admission")
        route=(root/"routes/privacy_controls.py").read_text()
        for marker in ("g.current_user.id","strict_consent_form","expected_record_id","expected_revision",
                       "csrf_token","10 per hour","ConsentStaleStateError","validate_form_token","consent_form_token"):
            if marker not in route: errors.append("Missing consent route control: "+marker)
        if "csrf.exempt" in route or "legal_approved" in route or "policy_version" in route:
            errors.append("Consent route accepts a forbidden bypass/policy selector")
        consent=(root/"services/consent.py").read_text()
        for marker in ("hmac.compare_digest", "asdict(self.policy)", "FORM_TTL_SECONDS", "issue_form_token"):
            if marker not in consent: errors.append("Missing signed consent form control: "+marker)
        generator=(root/"services/cover_letter_ai.py").read_text()
        if generator.count("ticket['admission_scope']") < 5:
            errors.append("Preview and result must bind the same admission scope")
        privacy=(root/"repositories/privacy.py").read_text()
        if '"ai_consents"' not in privacy or "AIConsent.user_id == user.id" not in privacy:
            errors.append("Privacy export/delete integration missing")
        template=(root/"templates/privacy/ai_consent.html").read_text()
        for marker in ("DRAFT","не является финальным","csrf_token()","expected_record_id","expected_revision"):
            if marker not in template: errors.append("Consent UI missing boundary: "+marker)
        if "|safe" in template: errors.append("Unsafe consent template")
        deferred=(root/"docs/LEGAL001_DEFERRED_DECISION.md").read_text()
        if "ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА" not in deferred:
            errors.append("Historical LEGAL-001 deferral was rewritten or removed")
        pg_workflow=(root/".github/workflows/legal001-postgresql.yml").read_text()
        for marker in ("postgres:17-alpine","tests/test_legal001_postgresql.py",
                       "T-06 PostgreSQL regressions","PG_DUMP_BIN","PG_RESTORE_BIN"):
            if marker not in pg_workflow: errors.append("Missing LEGAL-001 PostgreSQL verification control: "+marker)
        workflow=(root/".github/workflows/ci.yml").read_text()
        if "Verify LEGAL-001 consent and admission controls" not in workflow or "check_legal001_package.py" not in workflow:
            errors.append("Missing LEGAL-001 CI gate")
        # CI_PASS is an allowed documented transition only with the exact
        # recorded code CI evidence; it never means production acceptance.
        errors.extend(validate_canonical(root))
    except (OSError,ValueError,KeyError,TypeError,AttributeError,SyntaxError) as exc:
        errors.append("Missing or invalid LEGAL-001 package: "+type(exc).__name__)
    return errors

if __name__=="__main__":
    errors=validate()
    print(json.dumps({"package":"LEGAL-001","status":"IMPLEMENTED",
        "production_legal_state":"DRAFT","real_data_enabled":False,
        "paid_provider_calls":0,"remote_ci":"NOT ATTESTED BY LOCAL CHECK",
        "ok":not errors,"errors":errors},indent=2))
    raise SystemExit(bool(errors))
