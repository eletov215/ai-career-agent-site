from __future__ import annotations

from pathlib import Path

from scripts import check_document_structure

ROOT = Path(__file__).resolve().parents[1]


def test_project_documents_follow_doc_std_001():
    assert check_document_structure.validate(ROOT) == []


def test_canonical_documents_have_metadata_tables():
    for relative in [
        "docs/PLAN_CURRENT.md",
        "docs/PROJECT_PASSPORT.md",
        "docs/INFRA001_IMPLEMENTATION.md",
        "docs/INFRA001_VPS_TEST.md",
        "docs/INFRA001_PROVIDER_DECISION.md",
        "docs/INFRA001_VERIFICATION_STATUS.md",
        "docs/OPS001_VERIFICATION_STATUS.md",
        "docs/SYNC001_IMPLEMENTATION.md",
        "docs/SYNC001_RUNBOOK.md",
        "docs/SYNC001_VERIFICATION_STATUS.md",
        "docs/SYNC002_IMPLEMENTATION.md",
        "docs/SYNC002_RUNBOOK.md",
        "docs/SYNC002_VERIFICATION_STATUS.md",
        "docs/SEARCH001_IMPLEMENTATION.md",
        "docs/SEARCH001_VERIFICATION_STATUS.md",
        "docs/SEARCH001_RUNBOOK.md",
        "docs/SEARCH001_CONTRACT_REFERENCE.md",
        "docs/SEARCH002_IMPLEMENTATION.md",
        "docs/SEARCH002_VERIFICATION_STATUS.md",
        "docs/SEARCH002_RUNBOOK.md",
        "docs/SEARCH002_DEDUP_REFERENCE.md",
        "docs/SEARCH003_IMPLEMENTATION.md",
        "docs/SEARCH003_VERIFICATION_STATUS.md",
        "docs/SEARCH003_RUNBOOK.md",
        "docs/SEARCH003_PAGINATION_REFERENCE.md",
        "docs/AUTH001_IMPLEMENTATION.md",
        "docs/AUTH001_VERIFICATION_STATUS.md",
        "docs/AUTH001_RUNBOOK.md",
        "docs/AUTH001_SECURITY_REFERENCE.md",
        "docs/AUTH002_IMPLEMENTATION.md",
        "docs/AUTH002_VERIFICATION_STATUS.md",
        "docs/AUTH002_RUNBOOK.md",
        "docs/AUTH002_SECURITY_REFERENCE.md",
        "docs/PROF001_IMPLEMENTATION.md",
        "docs/PROF001_VERIFICATION_STATUS.md",
        "docs/PROF001_RUNBOOK.md",
        "docs/PROF001_PROFILE_REFERENCE.md",
        "docs/PROF002_IMPLEMENTATION.md",
        "docs/PROF002_VERIFICATION_STATUS.md",
        "docs/PROF002_RUNBOOK.md",
        "docs/PROF002_EXTRACTION_REFERENCE.md",
        "docs/PROF002_SECURITY_REFERENCE.md",
        "docs/PROF003_IMPLEMENTATION.md",
        "docs/PROF003_VERIFICATION_STATUS.md",
        "docs/PROF003_RUNBOOK.md",
        "docs/PROF003_RESUME_REFERENCE.md",
        "docs/PROF003_SECURITY_REFERENCE.md",
        "docs/PRIV001_IMPLEMENTATION.md",
        "docs/PRIV001_VERIFICATION_STATUS.md",
        "docs/PRIV001_RUNBOOK.md",
        "docs/PRIV001_PRIVACY_REFERENCE.md",
        "docs/PRIV001_SECURITY_REFERENCE.md",
        "docs/AI_BENCH_VERIFICATION_STATUS.md",
        "docs/SOURCE_AUDIT.md",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "| Поле | Значение |" in text
