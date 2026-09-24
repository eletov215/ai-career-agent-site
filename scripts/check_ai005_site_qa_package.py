#!/usr/bin/env python3
"""Dependency-free AI-005 SITE QA package guard. Never performs provider I/O."""
from __future__ import annotations
from pathlib import Path
import ast
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.ai005_site_qa_boundary import successor_hashes


def validate(root=ROOT):
    errors=[]
    try:
        successors=successor_hashes(root)
        if set(successors)!={"app.py","repositories/cover_letters.py"}:
            errors.append("Unexpected successor set")
        if 'REAL_DATA_SUPPORTED = False' not in (root/"domain/ai.py").read_text():
            errors.append("Real-data boundary changed")
        policy=(root/"services/legal_policy.py").read_text()
        if 'release_state="DRAFT"' not in policy:
            errors.append("Legal policy activated")
        app=(root/"app.py").read_text()
        for marker in (
            "admission=LegalLetterAdmission(CONSENT_SERVICE)",
            "LETTER_RUNTIME = LetterRuntime(AI_SERVICE)",
            "AliceSiteQAService(",
            "create_alice_site_qa_blueprint(SETTINGS, ALICE_SITE_QA_SERVICE)",
        ):
            if marker not in app:errors.append("Missing app control: "+marker)
        service=(root/"services/alice_site_qa.py").read_text()
        for marker in ("SyntheticLetterAdmission(user_id)","synthetic_cases()","confirmed=True"):
            if marker not in service:errors.append("Missing synthetic service control: "+marker)
        route=(root/"routes/alice_site_qa.py").read_text()
        for marker in ("is_search_admin","login_required","csrf_token","10 per hour","strict_form"):
            if marker not in route:errors.append("Missing QA route control: "+marker)
        if "csrf.exempt" in route or "candidate_fact" in route or "payload" in route:
            errors.append("QA route accepts or bypasses unsafe input")
        preview=(root/"templates/alice_qa/preview.html").read_text()
        if 'name="confirm"' in preview or "Создать черновик с Алисой" not in preview:
            errors.append("SITE QA must use one ordinary action without confirmation checkbox")
        if "|safe" in preview:
            errors.append("Unsafe QA template")
        repo=(root/"repositories/cover_letters.py").read_text()
        for marker in ("synthetic_site_qa","create_synthetic_qa","synthetic_cases()"):
            if marker not in repo:errors.append("Missing fixed-fixture repository control: "+marker)
        for rel in ("services/alice_site_qa.py","routes/alice_site_qa.py"):
            tree=ast.parse((root/rel).read_text())
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            if any(name.startswith(("requests","httpx","urllib.request","models")) for name in imports):
                errors.append("Unexpected QA-layer dependency: "+rel)
        workflow=(root/".github/workflows/ci.yml").read_text()
        if "check_ai005_site_qa_package.py" not in workflow or "test_ai005_site_qa.py" not in workflow:
            errors.append("Missing SITE QA CI gate")
    except (OSError,ValueError,KeyError,TypeError,AttributeError,SyntaxError,json.JSONDecodeError):
        errors.append("Missing or invalid AI-005 SITE QA package evidence")
    return errors


if __name__=="__main__":
    errors=validate()
    print(json.dumps({
        "package":"AI-005-SITE-QA","scope":"synthetic_only","ok":not errors,
        "paid_provider_calls":0,"real_data_enabled":False,
        "remote_ci":"NOT ATTESTED BY LOCAL CHECK","errors":errors
    },indent=2))
    raise SystemExit(bool(errors))
