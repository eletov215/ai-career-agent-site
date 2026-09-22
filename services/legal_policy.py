"""Reviewed-code LEGAL-001 AI consent policy descriptor.

This is deliberately a DRAFT technical disclosure. It is not final legal text and
cannot be activated by environment variables, request fields, or a user action.
"""
from __future__ import annotations
import hashlib
from domain.ai import PROVIDER
from domain.consent import AIConsentPolicy

DRAFT_NOTICE = """LEGAL-001 DRAFT / PLACEHOLDER REQUIRED.
Purpose: create a cover-letter proposal for the owner to review.
External provider: Yandex AI Studio / Alice AI LLM.
Potential data categories: selected confirmed career-profile facts and the saved
vacancy snapshot fields required by the cover-letter contract.
Excluded by the current contract: structured contacts, vacancy notes, resume
drafts, vacancy match scores, provider raw responses and credentials.
This draft does not activate production real-data AI processing.
"""

CURRENT_AI_CONSENT_POLICY = AIConsentPolicy(
    consent_type="external_ai_processing",
    scope="cover_letter_drafting",
    version="legal001-draft-2026-09-22-v1",
    document_hash=hashlib.sha256(DRAFT_NOTICE.encode("utf-8")).hexdigest(),
    provider=PROVIDER,
    purpose="cover_letter_proposal_generation",
    release_state="DRAFT",
    data_categories=("selected_confirmed_profile_facts", "saved_vacancy_snapshot"),
    display_label="LEGAL-001 DRAFT / PLACEHOLDER REQUIRED",
)
