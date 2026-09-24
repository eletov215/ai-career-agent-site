"""LEGAL-001 successor hashes authorized from the accepted AI-005 baseline."""
from pathlib import Path
import hashlib
import json

PREVIOUS_EXISTING={
    "app.py":"1b3527d6aa4725a0801e9209d6803bc485a6f5dfd645c8bd4fcd361519caa749",
    "database.py":"84bc8182c749c225c510d76416d9bb3aefd9b04b7b9da8910a1c4c65726fe947",
    "models/__init__.py":"5f1e851ce9d5e1a0b0163aa276d27324a69a9ca4501e091d8cc7d44fecc7bf66",
    "repositories/__init__.py":"977815ca49d879d275e6afcdc5422234d24ec87ef79391250b919fcb68d454c9",
    "repositories/privacy.py":"e52ca53338a37f793e2ce93862ef946378896cbc5f41949652bd336f77d5a858",
    "services/privacy.py":"4828acb4635d9f4b19f9b079b409814dde01182331424bbed28c39a4e775b53d",
    "services/storage.py":"27bc958a32c07d6c9c0db973ed4f1fb03c04f650b2f6a8f16a877870adc9e32a",
    "services/ai/letter_admission.py":"df9d3ee915df579341a8b29c8888e205b63e4f11fcef219b98c12207e8902fa8",
    "routes/privacy_controls.py":"5ac8056b892e816f7a548350e3111940354f1a182044adf3e354f18d566e6099",
    "templates/privacy/center.html":"756924e30a9e64d7c254ca79bc3d1253dadea55203835fae96e49a0862fec067",
    "services/cover_letter_ai.py":"9995a750518f06eec81f91e92e8ceddf889eb21fc29c8245b9ad94c11c163dd5",
}

EXPECTED_EXISTING={
    "app.py":"170140c8c17b8fbb949f9e4b50be7adbc7ef2d9d9aa393b24584fe075eb14820",
    "database.py":"08ccc3b8b561067562bd74a18ac56d78d1c6c1735a0ca12f7a66716a85a63620",
    "models/__init__.py":"7383d8190fd9e085d4e003993958e26bfde448085d92385a64d8654da9b697ac",
    "repositories/privacy.py":"2df3c3fc02dbec9e0a5289cb98860f764705bd6d3d05c5f324715553762015c8",
    "services/privacy.py":"14f272f0c47b850d21c2c9d06186d1533857c0c0d931a00de7beaeca2b4f6a16",
    "services/storage.py":"a1480f0977cca00e7e7218b84f92cd35d659f6cb0743ab6a65b28258ec20bd0c",
    "services/ai/letter_admission.py":"4671977d06b8a041091f85fe6a162dd420c9defa48affc3801441dccdd07c41c",
    "repositories/__init__.py":"ddf9d237ad13a75b362d6d4fabc68617294e4e92c26fca59b87fa89446d73235",
    "routes/privacy_controls.py":"a9d806588c2ef6b7259b7745e8ff59710b82dc4f0b62424eff8fa4659d79e9e7",
    "templates/privacy/center.html":"1456023b9e3db561eab1416f6041fe5c2f975b3ad412fb29c40147bb33614fbc",
    "services/cover_letter_ai.py":"de1fd9365a0515ab3f31d0bada43c2001a58a04bc8eec421b9ae04b50d5d97a3",
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
    site_qa={}
    if (root/"docs/evidence/ai-005-site-qa/change_boundary.json").is_file():
        from scripts.ai005_site_qa_boundary import successor_hashes as site_qa_successor_hashes
        site_qa=site_qa_successor_hashes(root)
    for rel,sha in EXPECTED_EXISTING.items():
        current=site_qa.get(rel,sha)
        if not _matches(root/rel,current):
            raise ValueError("LEGAL-001 successor hash mismatch: "+rel)
    return {**EXPECTED_EXISTING,**site_qa}
