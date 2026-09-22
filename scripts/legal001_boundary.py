"""LEGAL-001 successor hashes authorized from the accepted AI-005 baseline."""
from pathlib import Path
import hashlib
import json

EXPECTED_EXISTING={
    "app.py":"a75c6e858a9ee03a181f79bf7c3d7e3343d0c179",
    "database.py":"9c24c8deabe2835ba0d66c871be410163ddb24f6",
    "models/__init__.py":"ac1b010edae64b08162ba7dc8f3edb1398f3d847",
    "repositories/privacy.py":"3d9b60f481eac0c6d3f36e6eb644affec444cd30",
    "services/privacy.py":"bc1a7e2c000690ff7bec4735eae63afa8da428f5",
    "services/storage.py":"31d9494fb5613f5e838fbda2f6380f56e9fc5064",
    "services/ai/letter_admission.py":"aaf1d7f270550a792fd24aebe23c3b0302beb097",
}

def _matches(path: Path, expected: str) -> bool:
    raw=path.read_bytes()
    return expected in {hashlib.sha256(raw).hexdigest(),hashlib.sha256(raw.replace(b"\r\n",b"\n")).hexdigest()}

def successor_hashes(root: Path) -> dict[str,str]:
    evidence=json.loads((root/"docs/evidence/legal-001/change_boundary.json").read_text())
    if (evidence.get("package")!="LEGAL-001"
            or evidence.get("source_commit")!="f5ce1f42836e3872854332324f2ebdd9c8934b36"
            or evidence.get("source_tree")!="350ddf3f136a490b6504fc962f64822ba1985a86"
            or evidence.get("schema")!="20260922_0021"
            or evidence.get("production_legal_state")!="DRAFT"
            or evidence.get("public_real_data_enabled") is not False
            or evidence.get("paid_provider_calls")!=0):
        raise ValueError("Invalid LEGAL-001 successor evidence")
    for rel,sha in EXPECTED_EXISTING.items():
        if not _matches(root/rel,sha):
            raise ValueError("LEGAL-001 successor hash mismatch: "+rel)
    return dict(EXPECTED_EXISTING)
