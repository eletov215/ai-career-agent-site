"""AI-005 SITE QA successor evidence over accepted LEGAL-001/HOST-001 main."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

SOURCE_COMMIT = "b828596c893d59a544f9678d7b45ab6ed7f44230"
SOURCE_TREE = "05fc57dd0294cd5814637cc6e61e864f2bba9d2d"
PREVIOUS_APP_BLOB = "a75c6e858a9ee03a181f79bf7c3d7e3343d0c179"
CURRENT_APP_BLOB = "4c36add8c06cbefe620fd207611d7d7b5e4ba0d2"
PREVIOUS_APP_SHA256 = "170140c8c17b8fbb949f9e4b50be7adbc7ef2d9d9aa393b24584fe075eb14820"
NEW_BLOBS = {
    "routes/ai005_site_qa.py": "a12b562e52adf617613e901cb3f6b2f65d3d0006",
    "services/ai/letter_site_qa.py": "d84fa9c85c2beb078ad7d1a34ad56b93e8954ac2",
    "templates/letters/site_qa_detail.html": "82a7366463761d51581fb9e87c4348b2c4760150",
    "templates/letters/site_qa_error.html": "1dedbb2591d872f269c19392e1a4d0b8b6c738b5",
    "templates/letters/site_qa_index.html": "55bdd61ab95e6ced3ff2eb3dcbf57fb9b5f3e8fb",
    "templates/letters/site_qa_preview.html": "206b81043502df24df18356f6dd018c577f49403",
    "templates/letters/site_qa_review.html": "3c0bfe5c0e7ba8d8126f3b53ca51f15fe56ffb13",
    "templates/letters/site_qa_version.html": "bc31aa1c1565eab3c6db4c9f372dceb6b6765716",
    "tests/test_ai005_site_qa.py": "1df9fce37ec972b8f2dccb193900fa8b2d99d0bb",
}


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def verify_successor(root: Path) -> dict[str, str]:
    data = json.loads((root / "docs/evidence/ai-005-site-qa/change_boundary.json").read_text())
    if (
        data.get("package") != "AI-005"
        or data.get("tranche") != "site-qa-synthetic"
        or data.get("source_commit") != SOURCE_COMMIT
        or data.get("source_tree") != SOURCE_TREE
        or data.get("previous_app_blob") != PREVIOUS_APP_BLOB
        or data.get("current_app_blob") != CURRENT_APP_BLOB
        or data.get("public_real_data_enabled") is not False
        or data.get("production_legal_state") != "DRAFT"
        or data.get("paid_provider_calls") != 0
        or data.get("terraform_apply") is not False
        or data.get("production_consent_mutations") != 0
    ):
        raise ValueError("Invalid AI-005 SITE QA successor evidence")
    app = root / "app.py"
    if git_blob(app) != CURRENT_APP_BLOB:
        raise ValueError("AI-005 SITE QA app successor hash mismatch")
    for rel, expected in NEW_BLOBS.items():
        path = root / rel
        if not path.is_file() or git_blob(path) != expected:
            raise ValueError("AI-005 SITE QA new-file hash mismatch: " + rel)
    return {"app.py": hashlib.sha256(app.read_bytes()).hexdigest()}
