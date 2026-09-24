"""AI-005 SITE QA successor boundary over accepted AI-005/LEGAL-001 runtime."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
BASE_COMMIT="b828596c893d59a544f9678d7b45ab6ed7f44230"
EXPECTED_PREVIOUS={
    "app.py":"170140c8c17b8fbb949f9e4b50be7adbc7ef2d9d9aa393b24584fe075eb14820",
    "repositories/cover_letters.py":"7c896d2c2bc9493a0aea1d3cfcea811b228480ad284361215ac983e86fb5c05a",
}
NEW_RUNTIME={
    "services/alice_site_qa.py",
    "routes/alice_site_qa.py",
    "templates/alice_qa/index.html",
    "templates/alice_qa/preview.html",
    "templates/alice_qa/error.html",
}
EVIDENCE=ROOT/"docs/evidence/ai-005-site-qa/change_boundary.json"


def _hash(path: Path) -> str:
    raw=path.read_bytes().replace(b"\r\n",b"\n")
    return hashlib.sha256(raw).hexdigest()


def successor_hashes(root: Path=ROOT) -> dict[str,str]:
    data=json.loads((root/"docs/evidence/ai-005-site-qa/change_boundary.json").read_text())
    if (data.get("package")!="AI-005-SITE-QA"
            or data.get("source_commit")!=BASE_COMMIT
            or data.get("scope")!="synthetic_only"
            or data.get("production_legal_state")!="DRAFT"
            or data.get("public_real_data_enabled") is not False
            or data.get("paid_provider_calls")!=0):
        raise ValueError("Invalid AI-005 SITE QA successor evidence")
    existing=data.get("existing_files",{})
    new=data.get("new_runtime_sha256",{})
    if set(existing)!=set(EXPECTED_PREVIOUS) or set(new)!=NEW_RUNTIME:
        raise ValueError("Invalid AI-005 SITE QA file boundary")
    result={}
    for rel,previous in EXPECTED_PREVIOUS.items():
        row=existing.get(rel,{})
        if row.get("previous_sha256")!=previous:
            raise ValueError("AI-005 SITE QA predecessor mismatch: "+rel)
        current=row.get("current_sha256")
        if not isinstance(current,str) or _hash(root/rel)!=current:
            raise ValueError("AI-005 SITE QA current hash mismatch: "+rel)
        result[rel]=current
    for rel,current in new.items():
        if not isinstance(current,str) or _hash(root/rel)!=current:
            raise ValueError("AI-005 SITE QA new runtime mismatch: "+rel)
    return result
