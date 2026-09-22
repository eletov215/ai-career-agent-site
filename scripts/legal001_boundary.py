"""LEGAL-001 successor hashes authorized from the accepted AI-005 baseline."""
from pathlib import Path
import hashlib
import json

EXPECTED_EXISTING={
    "app.py":"170140c8c17b8fbb949f9e4b50be7adbc7ef2d9d9aa393b24584fe075eb14820",
    "database.py":"08ccc3b8b561067562bd74a18ac56d78d1c6c1735a0ca12f7a66716a85a63620",
    "models/__init__.py":"7383d8190fd9e085d4e003993958e26bfde448085d92385a64d8654da9b697ac",
    "repositories/privacy.py":"2df3c3fc02dbec9e0a5289cb98860f764705bd6d3d05c5f324715553762015c8",
    "services/privacy.py":"14f272f0c47b850d21c2c9d06186d1533857c0c0d931a00de7beaeca2b4f6a16",
    "services/storage.py":"a1480f0977cca00e7e7218b84f92cd35d659f6cb0743ab6a65b28258ec20bd0c",
    "services/ai/letter_admission.py":"7c2017782ea38f997ef16c63999c3bafd1a3d510fef2db53a9317c23a02ee610",
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
