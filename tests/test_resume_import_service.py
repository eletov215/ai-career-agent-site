from __future__ import annotations

from dataclasses import asdict
import json

import pytest

from services.profile import CareerProfileService
from services.resume_import import (
    ResumeImportReviewSigner,
    ResumeImportReviewTokenError,
    ResumeImportService,
)
from services.resume_parser import ParsedResume


RESUME_TEXT = """
Jane Doe
Backend Engineer
jane.doe@example.test
+375 29 123 45 67
Location: Minsk, Belarus

Summary
Backend engineer building reliable APIs and data services.

Skills
Python, SQL, PostgreSQL, Docker

Work Experience
Example Labs
Backend Engineer
January 2022 - present
Built REST APIs and improved reliability.

Education
Example University
Bachelor
Computer Science
2014 - 2018

Languages
English B2
Russian native
""".strip()


def _empty_profile(user_id: str = "owner-1"):
    class EmptyRepository:
        def get_by_user(self, _user_id):
            return None

    return CareerProfileService(EmptyRepository()).get(user_id)


def test_resume_import_builds_editable_structured_proposal_without_confirmation():
    service = ResumeImportService(max_pages=20, max_text_characters=200_000)
    proposal = service.propose(
        parsed=ParsedResume(filename="resume.pdf", page_count=1, text=RESUME_TEXT),
        current_profile=_empty_profile(),
    )

    assert proposal.filename == "resume.pdf"
    assert proposal.payload["headline"] == "Backend-разработчик"
    assert proposal.payload["contacts"]["contact_email"] == "jane.doe@example.test"
    assert proposal.payload["geography"]["current_location"] == "Minsk, Belarus"
    assert {item["name"] for item in proposal.payload["skills"]} >= {
        "Python",
        "SQL",
        "PostgreSQL",
        "Docker",
    }
    assert proposal.payload["employment"][0]["company"] == "Example Labs"
    assert proposal.payload["employment"][0]["position"] == "Backend Engineer"
    assert proposal.payload["employment"][0]["current"] is True
    assert proposal.payload["education"][0]["institution"] == "Example University"
    assert {item["name"] for item in proposal.payload["languages"]} >= {
        "Английский",
        "Русский",
    }
    assert "employment" in proposal.detected_sections
    assert proposal.signals


def test_resume_import_preserves_confirmed_scalars_and_reports_conflicts():
    class Current:
        version = 3
        def snapshot(self):
            snapshot = _empty_profile().snapshot()
            snapshot["headline"] = "Confirmed product manager"
            snapshot["contacts"]["contact_email"] = "confirmed@example.test"
            snapshot["skills"] = [{"name": "Roadmaps", "level": "advanced"}]
            return snapshot

    service = ResumeImportService(max_pages=20, max_text_characters=200_000)
    proposal = service.propose(
        parsed=ParsedResume(filename="resume.pdf", page_count=1, text=RESUME_TEXT),
        current_profile=Current(),
    )

    assert proposal.payload["headline"] == "Confirmed product manager"
    assert proposal.payload["contacts"]["contact_email"] == "confirmed@example.test"
    assert any(item.path == "core.headline" for item in proposal.conflicts)
    assert any(item.path == "contacts.contact_email" for item in proposal.conflicts)
    assert {item["name"] for item in proposal.payload["skills"]} >= {"Roadmaps", "Python"}


def test_review_token_is_owner_bound_timed_and_contains_only_bounded_metadata():
    service = ResumeImportService(max_pages=20, max_text_characters=200_000)
    proposal = service.propose(
        parsed=ParsedResume(filename="secret-name.pdf", page_count=1, text=RESUME_TEXT),
        current_profile=_empty_profile(),
    )
    signer = ResumeImportReviewSigner("test-secret-key")
    token = signer.dumps(proposal, owner_user_id="owner-a", base_profile_version=4)
    metadata = signer.loads(token, owner_user_id="owner-a")

    assert metadata.base_profile_version == 4
    assert len(metadata.owner_fingerprint) == 64
    assert metadata.extractor_version == "deterministic-text-v1"
    serialized = json.dumps(asdict(metadata), ensure_ascii=False)
    assert "secret-name.pdf" not in serialized
    assert "jane.doe@example.test" not in serialized
    assert "Built REST APIs" not in serialized

    with pytest.raises(ResumeImportReviewTokenError, match="другому аккаунту"):
        signer.loads(token, owner_user_id="owner-b")
    with pytest.raises(ResumeImportReviewTokenError):
        signer.loads(token + "tampered", owner_user_id="owner-a")
    with pytest.raises(ResumeImportReviewTokenError, match="истёк"):
        signer.loads(token, owner_user_id="owner-a", max_age=-1)
