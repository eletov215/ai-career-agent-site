"""Dependency-free assertions do not substitute for route/runtime QA."""
from pathlib import Path
import shutil
import pytest

from scripts.ai004_m04b_successor import M04BSuccessorError, validate_successor

from scripts.check_ai005_site_qa_package import PROTECTED, RUNTIME, validate

ROOT=Path(__file__).resolve().parents[1]


def test_site_qa_package_boundary():
    assert validate(ROOT)==[]


def test_site_qa_guard_rejects_changed_legal_source(tmp_path):
    paths=set(PROTECTED)|RUNTIME|{'services/ai/site_qa_gate.py', 'routes/admin_sources.py', 'scripts/check_ai_provider_package.py', '.github/workflows/ai005-site-qa.yml',
                                'docs/evidence/ai-005-site-qa/change_boundary.json', 'docs/evidence/ai-005-site-qa-no-logging/change_boundary.json',
                                    'docs/evidence/ai-005-live-qa-001/change_boundary.json',
                                    'docs/evidence/ai-005-validation-reasons/change_boundary.json',
                                    'docs/evidence/ai-005-vacancy-evidence-prompt/change_boundary.json',
                                    'docs/evidence/ai-006-grounding-hardening/change_boundary.json',
                                    'scripts/check_ai005_live_qa_boundary.py',
                                'scripts/check_ai005_site_qa_package.py', 'domain/ai.py'}
    for rel in paths:
        dest=tmp_path/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
    from tests.ai005_boundary_helper import copy_job002_boundary
    copy_job002_boundary(ROOT, tmp_path)
    assert validate(tmp_path)==[]
    p=tmp_path/'domain/ai.py';p.write_text(p.read_text().replace('REAL_DATA_SUPPORTED = False','REAL_DATA_SUPPORTED = True'))
    # The versioned successor now catches any edit to the immutable legal
    # activation flag BEFORE the inherited AI-005 SITE-QA package validates
    # the old protected predecessor. Both guards must still reject the edit.
    with pytest.raises(M04BSuccessorError, match=r"^historical_evidence_changed:domain/ai\\.py$"):
        validate_successor(tmp_path)
    assert validate(tmp_path) != []


def test_provider_successor_is_narrow_and_requires_complete_evidence(tmp_path):
    from scripts.check_ai005_site_qa_package import successor_hashes
    assert set(successor_hashes(ROOT)) == {'routes/admin_sources.py'}
    paths=set(PROTECTED)|RUNTIME|{'services/ai/site_qa_gate.py', 'routes/admin_sources.py', 'scripts/check_ai_provider_package.py',
        '.github/workflows/ai005-site-qa.yml','docs/evidence/ai-005-site-qa/change_boundary.json',
        'docs/evidence/ai-005-site-qa-no-logging/change_boundary.json',
        'docs/evidence/ai-005-live-qa-001/change_boundary.json', 'scripts/check_ai005_live_qa_boundary.py',
        'docs/evidence/ai-005-vacancy-evidence-prompt/change_boundary.json',
        'docs/evidence/ai-006-grounding-hardening/change_boundary.json',
        'scripts/check_ai005_site_qa_package.py', 'domain/ai.py'}
    for rel in paths:
        dest=tmp_path/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
    from tests.ai005_boundary_helper import copy_job002_boundary
    copy_job002_boundary(ROOT, tmp_path)
    p=tmp_path/'routes/admin_sources.py';p.write_text(p.read_text().replace('"no-store, max-age=0"','"public"'))
    import pytest
    with pytest.raises(ValueError):successor_hashes(tmp_path)
