"""AI004-M04B: owner-locked saved-vacancy matching storage, no AI dispatch.

Only JOB-001 owner-qualified, non-truncated source snapshots are supported.
SEARCH-only matching requires a separate owner-qualified adapter (M05).
No HTTP routes call this repository and it does not perform legal admission.

The successful-result callback is designed for AIRepository.settle(on_success):
report insertion + ready-cache transition take place inside the SAME
transaction as the ledger settlement, never around an external provider call.
"""
from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import delete, func, select, text

from domain.ai import REAL_DATA_SUPPORTED
from domain.saved_vacancy import SavedVacancyError
from domain.vacancy_match import MATCH_VERSION
from models import ResumeDraft, ResumeVersion, SavedVacancy, User
from models.ai import AIUsageEvent
from models.user_match import UserMatchCache, UserMatchReport
from repositories.base import RepositoryBase
from repositories.saved_vacancies import saved_view
from services.matching_cache_keys import (
    MatchCacheKeyError, MatchCacheAddress, build_cache_address,
    build_operation_hash, seal_validated_result, verify_sealed_result,
)
from services.matching_contract import (
    CLASSIFICATION_VERSION, ClassificationContract, ClassificationContractError,
    build_classification_contract, canonical_json,
)
from services.matching_input import MatchInputError, project_resume_version, project_saved_vacancy
from services.matching_validation import validate_classification

MAX_USER_MATCH_REPORTS = 100
MAX_USER_MATCH_CLAIMS = 150
MAX_STORED_RESULT_BYTES = 128_000
MAX_CLAIM_LEASE_SECONDS = 1800
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class UserMatchStorageError(ValueError):
    """Fixed code only, never embeds private resume/vacancy/provider text."""


def report_export_view(row: UserMatchReport) -> dict[str, Any]:
    """Owner-authorised export projection without internal HMAC/ledger tokens."""
    try:
        report = json.loads(row.result_json)
        serialized = canonical_json(report)
        if (hashlib.sha256(serialized.encode("utf-8")).hexdigest() != row.result_hash
                or not isinstance(report, dict)
                or report.get("source_hash") != row.source_hash
                or report.get("resume_hash") != row.resume_hash
                or report.get("vacancy_hash") != row.vacancy_hash
                or report.get("classification_version") != row.classification_version
                or report.get("summary", {}).get("policy_version") != row.scoring_version
                or report.get("presentation") != "source_quotes_and_code_labels"
                or not isinstance(report.get("requirements"), list)):
            raise ValueError("corrupt")
    except (TypeError, ValueError, AttributeError, KeyError):
        raise UserMatchStorageError("invalid_saved_report") from None
    return {
        "id": row.id,
        "resume_version_id": row.resume_version_id,
        "saved_vacancy_id": row.saved_vacancy_id,
        "source_kind": row.source_kind,
        "source_hash": row.source_hash,
        "resume_hash": row.resume_hash,
        "vacancy_hash": row.vacancy_hash,
        "classification_version": row.classification_version,
        "scoring_version": row.scoring_version,
        "result_hash": row.result_hash,
        "result": report,
        "created_at": row.created_at,
    }


def cache_export_view(row: UserMatchCache) -> dict[str, Any]:
    """Expose user-visible history state, never cache HMAC or operation hash."""
    return {
        "id": row.id,
        "resume_version_id": row.resume_version_id,
        "saved_vacancy_id": row.saved_vacancy_id,
        "source_kind": row.source_kind,
        "state": row.state,
        "report_id": row.report_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


class UserMatchRepository(RepositoryBase):
    """Private owner-scoped persistence primitive, not a provider/runtime gate."""

    def __init__(self, database, *, fingerprint_key: bytes):
        super().__init__(database)
        if not isinstance(fingerprint_key, bytes) or len(fingerprint_key) < 32:
            raise ValueError("HMAC key is required")
        self.key = fingerprint_key

    @contextmanager
    def _write(self, user_id: str):
        with self.session() as session:
            try:
                if self.engine.dialect.name == "sqlite":
                    session.execute(text("BEGIN IMMEDIATE"))
                elif self.engine.dialect.name == "postgresql":
                    session.execute(text("SET LOCAL lock_timeout = '5s'"))
                self._owner(session, user_id, lock=True)
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    @staticmethod
    def _owner(session, user_id: str, *, lock: bool = False):
        stmt = select(User).where(User.id == user_id)
        if lock:
            stmt = stmt.with_for_update()
        owner = session.scalar(stmt)
        if owner is None or owner.status != "active" or owner.email_verified_at is None:
            raise UserMatchStorageError("verified_account_required")
        return owner

    def _source(self, session, user_id: str, resume_version_id: str,
                saved_vacancy_id: str) -> tuple[ClassificationContract, MatchCacheAddress, str]:
        """Resolve both sources ONLY from owner-held ORM rows, never browser JSON."""
        version = session.scalar(
            select(ResumeVersion)
            .join(ResumeDraft, ResumeDraft.id == ResumeVersion.draft_id)
            .where(
                ResumeVersion.id == resume_version_id,
                ResumeDraft.user_id == user_id,
            )
        )
        saved_row = session.scalar(select(SavedVacancy).where(
            SavedVacancy.id == saved_vacancy_id, SavedVacancy.user_id == user_id,
        ))
        if version is None or saved_row is None:
            raise UserMatchStorageError("not_found")
        if hashlib.sha256(version.snapshot_json.encode("utf-8")).hexdigest() != version.content_hash:
            raise UserMatchStorageError("invalid_source")
        try:
            snapshot = saved_view(saved_row)["snapshot"]
            truncated = snapshot.get("truncated_fields")
            sources = snapshot.get("source_records")
            if (not isinstance(truncated, list) or "requirements" in truncated
                    or not isinstance(sources, list) or not sources):
                raise UserMatchStorageError("incomplete_source")
            source_ids = [record.get("identity_hash") for record in sources
                          if isinstance(record, dict)]
            if (len(source_ids) != len(sources)
                    or len(set(source_ids)) != len(source_ids)
                    or any(not isinstance(key, str) or not _SHA256.fullmatch(key)
                           for key in source_ids)):
                raise UserMatchStorageError("invalid_source")
            identity = hashlib.sha256(
                canonical_json(sorted(source_ids)).encode("utf-8")
            ).hexdigest()
            resume = project_resume_version({"snapshot_json": version.snapshot_json})
            vacancy = project_saved_vacancy({"snapshot": snapshot})
            contract = build_classification_contract(resume, vacancy, source_complete=True)
            address = build_cache_address(
                secret=self.key, user_id=user_id,
                resume_version_id=resume_version_id,
                vacancy_identity_hash=identity, contract=contract,
            )
        except (SavedVacancyError, MatchInputError, ClassificationContractError,
                MatchCacheKeyError, UnicodeError, TypeError, ValueError) as exc:
            if isinstance(exc, UserMatchStorageError):
                raise
            raise UserMatchStorageError("invalid_source") from None
        return contract, address, identity

    @staticmethod
    def _cache_view(row: UserMatchCache) -> dict[str, Any]:
        return cache_export_view(row)

    @staticmethod
    def _check_cache_link(row: UserMatchCache, *, user_id: str,
                          resume_version_id: str, saved_vacancy_id: str,
                          address: MatchCacheAddress, identity: str) -> None:
        """Defend against a cache row pointing at another source or owner."""
        if (row.user_id != user_id or row.source_kind != "saved"
                or row.resume_version_id != resume_version_id
                or row.saved_vacancy_id != saved_vacancy_id
                or row.vacancy_identity_hash != identity
                or row.cache_key_hash != address.cache_key_hash
                or row.request_hash != address.request_hash
                or row.source_hash != address.source_hash):
            raise UserMatchStorageError("invalid_saved_report")

    def _report_checked(
        self, session, row: UserMatchCache,
        contract: ClassificationContract, address: MatchCacheAddress,
    ) -> dict[str, Any]:
        if row.state != "ready" or row.report_id is None:
            raise UserMatchStorageError("invalid_saved_report")
        report = session.scalar(select(UserMatchReport).where(
            UserMatchReport.id == row.report_id,
            UserMatchReport.user_id == row.user_id,
        ))
        if report is None:
            raise UserMatchStorageError("invalid_saved_report")
        if (report.cache_key_hash != row.cache_key_hash
                or report.resume_version_id != row.resume_version_id
                or report.saved_vacancy_id != row.saved_vacancy_id
                or report.vacancy_identity_hash != row.vacancy_identity_hash
                or report.source_kind != row.source_kind
                or report.source_hash != contract.source_hash
                or row.source_hash != contract.source_hash
                or report.classification_version != CLASSIFICATION_VERSION
                or report.scoring_version != MATCH_VERSION):
            raise UserMatchStorageError("invalid_saved_report")
        export = report_export_view(report)
        if not verify_sealed_result(
            secret=self.key, address=address,
            report=export["result"], signature=report.result_seal,
        ):
            raise UserMatchStorageError("invalid_saved_report")
        return export

    def claim_saved(self, *, user_id: str, resume_version_id: str,
                    saved_vacancy_id: str, owner_action_nonce: str,
                    now: int, lease_seconds: int = 300) -> dict[str, Any]:
        """Unique pending claim. A pending/unknown/failed hit is NEVER retried.

        This is an internal store primitive, NOT consent or budget admission.
        Callers in M05 must separately check these gates before provider I/O.
        """
        if (type(now) is not int or now < 0
                or type(lease_seconds) is not int
                or not 1 <= lease_seconds <= MAX_CLAIM_LEASE_SECONDS):
            raise UserMatchStorageError("invalid_request")
        with self._write(user_id) as session:
            contract, address, identity = self._source(
                session, user_id, resume_version_id, saved_vacancy_id,
            )
            operation_hash = build_operation_hash(
                secret=self.key, address=address,
                owner_action_nonce=owner_action_nonce,
            )
            row = session.scalar(select(UserMatchCache).where(
                UserMatchCache.user_id == user_id,
                UserMatchCache.cache_key_hash == address.cache_key_hash,
            ))
            if row is not None:
                self._check_cache_link(
                    row, user_id=user_id, resume_version_id=resume_version_id,
                    saved_vacancy_id=saved_vacancy_id,
                    address=address, identity=identity,
                )
                if row.state == "ready":
                    self._report_checked(session, row, contract, address)
                response = self._cache_view(row)
                # An expired reservation is NEVER automatically replayed.
                if row.state == "pending" and row.lease_expires_at <= now:
                    row.state = "unknown"
                    row.updated_at = now
                    response["state"] = "unknown"
                return response

            total = session.scalar(select(func.count()).select_from(UserMatchCache).where(
                UserMatchCache.user_id == user_id,
            )) or 0
            if total >= MAX_USER_MATCH_CLAIMS:
                raise UserMatchStorageError("history_limit")
            row = UserMatchCache(
                id=str(uuid4()), user_id=user_id, resume_version_id=resume_version_id,
                saved_vacancy_id=saved_vacancy_id, source_kind="saved",
                vacancy_identity_hash=identity,
                cache_key_hash=address.cache_key_hash,
                request_hash=address.request_hash,
                operation_hash=operation_hash, source_hash=address.source_hash,
                state="pending", report_id=None,
                lease_expires_at=now + lease_seconds, created_at=now, updated_at=now,
            )
            session.add(row)
            session.flush()
            return self._cache_view(row)

    def load_saved(self, *, user_id: str, resume_version_id: str,
                   saved_vacancy_id: str, now: int) -> dict[str, Any] | None:
        """No writes, no provider. An expired pending row displays unknown."""
        if type(now) is not int or now < 0:
            raise UserMatchStorageError("invalid_request")
        with self.session() as session:
            self._owner(session, user_id)
            contract, address, identity = self._source(
                session, user_id, resume_version_id, saved_vacancy_id,
            )
            row = session.scalar(select(UserMatchCache).where(
                UserMatchCache.user_id == user_id,
                UserMatchCache.cache_key_hash == address.cache_key_hash,
            ))
            if row is None:
                return None
            self._check_cache_link(
                row, user_id=user_id, resume_version_id=resume_version_id,
                saved_vacancy_id=saved_vacancy_id,
                address=address, identity=identity,
            )
            view = self._cache_view(row)
            if row.state == "ready":
                view["report"] = self._report_checked(session, row, contract, address)
            elif row.state == "pending" and row.lease_expires_at <= now:
                view["state"] = "unknown"
            return view

    def settle_ready_in_session(self, session, *, claim_id: str,
                                event: AIUsageEvent, validated: Mapping[str, Any],
                                now: int) -> str:
        """Call from AIRepository.settle(on_success=...). Never commit here.

        A successful ledger settlement and an immutable report are all-or-nothing
        in the caller's transaction. No separate post-settlement save is allowed.
        """
        if (type(now) is not int or now < 0 or not isinstance(event, AIUsageEvent)
                or event.status != "reserved" or event.task != "vacancy_match"
                or event.fixture_id != "general-vacancy-match"):
            raise UserMatchStorageError("invalid_usage_link")
        stmt = select(UserMatchCache).where(
            UserMatchCache.id == claim_id,
            UserMatchCache.user_id == event.user_id,
        ).with_for_update()
        row = session.scalar(stmt)
        if (row is None or row.state != "pending"
                or row.lease_expires_at <= now
                or row.operation_hash != event.idempotency_hash
                or row.request_hash != event.request_hash
                or row.source_kind != "saved" or row.saved_vacancy_id is None):
            raise UserMatchStorageError("invalid_claim")
        self._owner(session, event.user_id)
        contract, address, identity = self._source(
            session, event.user_id, row.resume_version_id, row.saved_vacancy_id,
        )
        if (row.source_hash != contract.source_hash
                or row.cache_key_hash != address.cache_key_hash
                or row.vacancy_identity_hash != identity):
            raise UserMatchStorageError("stale_source")
        if not isinstance(validated, Mapping):
            raise UserMatchStorageError("invalid_saved_report")
        # Do NOT assume a caller-supplied percentage/evidence remains valid.
        try:
            raw = canonical_json({
                "contract_version": CLASSIFICATION_VERSION,
                "source_hash": contract.source_hash,
                "classifications": [{
                    "requirement_id": item["requirement_id"],
                    "status": item["status"],
                    "candidate_evidence": item["candidate_evidence"],
                } for item in validated["requirements"]],
            })
            rebuilt = validate_classification(raw, contract)
            if canonical_json(rebuilt) != canonical_json(validated):
                raise ValueError("noncanonical")
            serialized = canonical_json(rebuilt)
            if len(serialized.encode("utf-8")) > MAX_STORED_RESULT_BYTES:
                raise ValueError("too_large")
            seal = seal_validated_result(
                secret=self.key, address=address, report=rebuilt,
            )
        except (KeyError, ValueError, TypeError, MatchCacheKeyError,
                ClassificationContractError):
            raise UserMatchStorageError("invalid_saved_report") from None

        report_count = session.scalar(select(func.count()).select_from(UserMatchReport).where(
            UserMatchReport.user_id == event.user_id,
        )) or 0
        if report_count >= MAX_USER_MATCH_REPORTS:
            raise UserMatchStorageError("history_limit")
        report = UserMatchReport(
            id=str(uuid4()), user_id=event.user_id,
            resume_version_id=row.resume_version_id,
            saved_vacancy_id=row.saved_vacancy_id, source_kind="saved",
            vacancy_identity_hash=identity,
            cache_key_hash=row.cache_key_hash,
            source_hash=address.source_hash,
            resume_hash=address.resume_hash,
            vacancy_hash=address.vacancy_hash,
            classification_version=CLASSIFICATION_VERSION,
            scoring_version=MATCH_VERSION,
            usage_event_id=event.id, result_json=serialized,
            result_hash=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            result_seal=seal, created_at=now,
        )
        session.add(report)
        session.flush()
        row.state = "ready"
        row.report_id = report.id
        row.lease_expires_at = 0
        row.updated_at = now
        session.flush()
        return report.id

    def close_claim(self, *, user_id: str, claim_id: str, now: int) -> dict[str, Any]:
        """Close a failed/unknown charge ONLY after its ledger event is settled."""
        if type(now) is not int or now < 0:
            raise UserMatchStorageError("invalid_request")
        with self._write(user_id) as session:
            row = session.scalar(select(UserMatchCache).where(
                UserMatchCache.user_id == user_id, UserMatchCache.id == claim_id,
            ).with_for_update())
            if row is None:
                raise UserMatchStorageError("not_found")
            if row.state != "pending":
                return self._cache_view(row)
            event = session.scalar(select(AIUsageEvent).where(
                AIUsageEvent.user_id == user_id,
                AIUsageEvent.idempotency_hash == row.operation_hash,
                AIUsageEvent.request_hash == row.request_hash,
            ))
            if event is None or event.status not in ("failed", "unknown"):
                raise UserMatchStorageError("unsettled_usage")
            row.state = "unknown" if event.status == "unknown" or event.cost_uncertain else "failed"
            row.updated_at = now
            return self._cache_view(row)

    def delete_report(self, *, user_id: str, report_id: str,
                      result_hash: str) -> None:
        """Explicit owner action. Composite FK cascades linked ready cache."""
        if not isinstance(result_hash, str) or not _SHA256.fullmatch(result_hash):
            raise UserMatchStorageError("invalid_request")
        with self._write(user_id) as session:
            row = session.scalar(select(UserMatchReport).where(
                UserMatchReport.id == report_id,
                UserMatchReport.user_id == user_id,
            ))
            if row is None:
                raise UserMatchStorageError("not_found")
            if row.result_hash != result_hash:
                raise UserMatchStorageError("stale_report")
            # Read/verify even if the deletion request has a matching digest.
            report_export_view(row)
            session.execute(delete(UserMatchReport).where(
                UserMatchReport.id == report_id,
                UserMatchReport.user_id == user_id,
            ))
