"""Admin-only synthetic Alice SITE QA using the production letter runtime."""
from __future__ import annotations

import secrets
import time
from uuid import UUID, uuid5

from sqlalchemy import select

from domain.cover_letter import LetterError, options
from domain.saved_vacancy import SNAPSHOT_VERSION, canonical_json, fingerprint
from models import User, SavedVacancy, SavedVacancySource
from repositories.cover_letters import CoverLetterRepository
from repositories.profiles import CareerProfileRepository
from services.ai.letter_admission import (
    SYNTHETIC_MANIFEST_SHA256,
    SyntheticLetterAdmission,
    synthetic_cases,
)
from services.ai.letter_runtime import LetterRuntime
from services.cover_letter_ai import CoverLetterGenerator
from services.cover_letters import CoverLetterService
from services.profile import CareerProfileService
from services.saved_vacancy_snapshot import build_snapshot

_SITE_QA_NAMESPACE = UUID("0df3c04a-4084-4fca-92bb-5897798b4fe5")
SITE_QA_FACT_ID = "profile.summary"


class AliceLetterSiteQA:
    """Persistent synthetic workspace isolated from the administrator's real data."""

    def __init__(self, repository: CoverLetterRepository, ai_service, *, signing_key: str, clock=time.time):
        if not signing_key:
            raise ValueError("Signing key is required")
        self.repository = repository
        self.ai_service = ai_service
        self.signing_key = signing_key
        self.clock = clock

    @staticmethod
    def _language(value: str) -> str:
        if value not in synthetic_cases():
            raise LetterError("invalid_options")
        return value

    def _owner_id(self, admin_id: str, language: str) -> str:
        language = self._language(language)
        scope = f"ai005-site-qa-v1:{SYNTHETIC_MANIFEST_SHA256}:{admin_id}:{language}"
        return str(uuid5(_SITE_QA_NAMESPACE, scope))

    def _saved_id(self, owner_id: str) -> str:
        return str(uuid5(_SITE_QA_NAMESPACE, "saved:" + owner_id))

    def _source_id(self, owner_id: str) -> str:
        return str(uuid5(_SITE_QA_NAMESPACE, "source:" + owner_id))

    def _ensure_fixture(self, admin_id: str, language: str) -> tuple[str, str]:
        language = self._language(language)
        case = synthetic_cases()[language]
        owner_id = self._owner_id(admin_id, language)
        saved_id = self._saved_id(owner_id)
        now = int(self.clock())
        raw = {
            "source": "hh",
            "external_id": f"ai005-site-qa-{language}",
            "url": f"https://hh.ru/vacancy/ai005-site-qa-{language}",
            **case["vacancy"],
            "location": "",
            "source_status": "active",
            "currency": "RUB",
        }
        snapshot = build_snapshot(raw)
        snapshot_hash = fingerprint(snapshot)

        with self.repository.session() as session, session.begin():
            user = session.get(User, owner_id)
            if user is None:
                session.add(User(
                    id=owner_id,
                    email=None,
                    normalized_email=None,
                    display_name="AI-005 synthetic site QA",
                    status="active",
                    email_verified_at=now,
                    password_hash=None,
                    created_at=now,
                    updated_at=now,
                ))
            elif user.email is not None or user.normalized_email is not None or user.password_hash is not None:
                raise LetterError("storage_integrity")

            saved = session.get(SavedVacancy, saved_id)
            if saved is None:
                session.add(SavedVacancy(
                    id=saved_id,
                    user_id=owner_id,
                    snapshot_json=canonical_json(snapshot),
                    snapshot_hash=snapshot_hash,
                    snapshot_version=SNAPSHOT_VERSION,
                    title=snapshot["title"],
                    company=snapshot["company"],
                    location=snapshot["location"],
                    search_text=" ".join((snapshot["title"], snapshot["company"], snapshot["location"])).casefold(),
                    note="",
                    revision=1,
                    created_at=now,
                    updated_at=now,
                ))
                src = snapshot["source_records"][0]
                session.add(SavedVacancySource(
                    id=self._source_id(owner_id),
                    saved_vacancy_id=saved_id,
                    user_id=owner_id,
                    source=src["source"],
                    external_id=src["external_id"],
                    identity_hash=src["identity_hash"],
                    url=src["url"],
                    created_at=now,
                ))
            elif (
                saved.user_id != owner_id
                or saved.snapshot_hash != snapshot_hash
                or saved.snapshot_version != SNAPSHOT_VERSION
            ):
                raise LetterError("storage_integrity")

        profile = CareerProfileService(CareerProfileRepository(self.repository.engine))
        current = profile.get(owner_id)
        expected_summary = case["candidate_facts"][0]["text"]
        if current.summary != expected_summary or not current.exists:
            profile.save(
                user_id=owner_id,
                payload={"summary": expected_summary},
                expected_version=current.version,
                now=now,
            )
        return owner_id, saved_id

    def _service(self, owner_id: str, *, generation: bool = True) -> CoverLetterService:
        generator = None
        if generation:
            generator = CoverLetterGenerator(
                self.repository,
                LetterRuntime(self.ai_service),
                signing_key=self.signing_key,
                admission=SyntheticLetterAdmission(owner_id),
                clock=self.clock,
            )
        return CoverLetterService(
            self.repository,
            signing_key=self.signing_key,
            clock=self.clock,
            generator=generator,
        )

    def start(self, admin_id: str, language: str, length: str, tone: str) -> dict:
        opts = options(language, length, tone)
        owner_id, saved_id = self._ensure_fixture(admin_id, language)
        service = self._service(owner_id)
        source = service.source(owner_id, saved_id)
        row = service.create(
            owner_id,
            saved_id,
            source["source_hash"],
            secrets.token_urlsafe(24),
            language,
            length,
            tone,
            confirmed=True,
        )
        preview = service.preview_generation(
            owner_id,
            row["id"],
            row["revision"],
            language,
            length,
            tone,
            [SITE_QA_FACT_ID],
        )
        return {"language": language, "letter": row, "preview": preview, "options": opts}

    def _owned(self, admin_id: str, language: str, letter_id: str) -> tuple[str, CoverLetterService, dict]:
        owner_id = self._owner_id(admin_id, language)
        service = self._service(owner_id)
        record = service.get(owner_id, letter_id)
        return owner_id, service, record

    def generate(self, admin_id: str, language: str, letter_id: str, review_token: str | None) -> dict:
        owner_id, service, _ = self._owned(admin_id, language, letter_id)
        # The button itself is the explicit user action. No redundant per-call checkbox.
        return service.generate(owner_id, letter_id, review_token=review_token, confirmed=True)

    def detail(self, admin_id: str, language: str, letter_id: str, proposal_id: str | None = None) -> dict:
        _owner_id, _service, record = self._owned(admin_id, language, letter_id)
        proposal = None
        if proposal_id:
            proposal = next((item for item in record["proposals"] if item["id"] == proposal_id), None)
            if proposal is None:
                raise LetterError("not_found")
            if proposal["base_revision"] != record["revision"] or record["source_stale"]:
                raise LetterError("stale_write")
        return {"record": record, "proposal": proposal}

    def accept(self, admin_id: str, language: str, letter_id: str, *, expected: str,
               proposal_id: str, subject: str, body: str, confirmed: bool) -> dict:
        owner_id, service, record = self._owned(admin_id, language, letter_id)
        proposal = next((item for item in record["proposals"] if item["id"] == proposal_id), None)
        if proposal is None:
            raise LetterError("not_found")
        opts = {key: proposal["content"][key] for key in ("language", "length", "tone")}
        return service.save(
            owner_id,
            letter_id,
            expected,
            subject,
            body,
            **opts,
            confirmed=confirmed,
            proposal_id=proposal_id,
        )

    def reject(self, admin_id: str, language: str, letter_id: str, proposal_id: str,
               *, expected: str, confirmed: bool) -> None:
        owner_id, service, _ = self._owned(admin_id, language, letter_id)
        service.reject(owner_id, letter_id, proposal_id, expected, confirmed=confirmed)

    def version(self, admin_id: str, language: str, letter_id: str, number: int) -> dict:
        owner_id, service, _ = self._owned(admin_id, language, letter_id)
        return service.version(owner_id, letter_id, number)

    def export(self, admin_id: str, language: str, letter_id: str, number: int) -> bytes:
        owner_id, service, _ = self._owned(admin_id, language, letter_id)
        return service.export_text(owner_id, letter_id, number)
