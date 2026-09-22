"""LEGAL-001 consent business logic."""
from __future__ import annotations
import re
import hashlib
import hmac
import json
from dataclasses import asdict
import time
from domain.consent import AIConsentPolicy
from repositories.consent import ConsentConflictError, ConsentOwnerNotFoundError, ConsentRepository
from services.legal_policy import CURRENT_AI_CONSENT_POLICY

class ConsentError(RuntimeError):
    pass
class ConsentStaleStateError(ConsentError):
    pass
class ConsentNotActiveError(ConsentError):
    pass

FORM_TTL_SECONDS = 900

_ID=re.compile(r"^[0-9a-fA-F-]{36}$")

class ConsentService:
    def __init__(self, repository: ConsentRepository, *, policy: AIConsentPolicy=CURRENT_AI_CONSENT_POLICY, clock=time.time):
        self.repository=repository;self.policy=policy;self.clock=clock

    def _form_signature(self, user_id, record_id, revision, action, issued, signing_key):
        if not isinstance(signing_key, str) or not signing_key:
            raise ConsentStaleStateError("invalid_form")
        message = json.dumps(
            ["legal001-form-v1", str(user_id), record_id, revision, action, issued,
             asdict(self.policy)], sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        return hmac.new(signing_key.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def issue_form_token(self, user_id, current, *, signing_key):
        """Bind the rendered policy, owner, action and optimistic state, not a client version."""
        record_id = current["id"] if current else None
        revision = current["revision"] if current else 0
        action = "withdraw" if current and current["status"] == "accepted" else "accept"
        issued = int(self.clock())
        signature = self._form_signature(user_id, record_id, revision, action, issued, signing_key)
        return str(issued) + "." + signature

    def validate_form_token(self, user_id, token, *, action, expected_record_id,
                            expected_revision, signing_key):
        """Reject old empty forms after policy changes as well as tampering/replay."""
        record_id, revision = self.expected_state(expected_record_id, expected_revision)
        try:
            if action not in ("accept", "withdraw") or not isinstance(token, str) or len(token) > 100:
                raise ValueError
            raw_issued, signature = token.split(".")
            if not raw_issued.isascii() or not raw_issued.isdecimal() or len(signature) != 64:
                raise ValueError
            issued = int(raw_issued)
            if not issued <= int(self.clock()) < issued + FORM_TTL_SECONDS:
                raise ValueError
            expected = self._form_signature(user_id, record_id, revision, action, issued, signing_key)
            if not hmac.compare_digest(signature, expected):
                raise ValueError
        except (ValueError, TypeError):
            raise ConsentStaleStateError("stale_state") from None

    @staticmethod
    def expected_state(record_id, revision):
        value=(record_id or "").strip();expected_id=value or None
        if expected_id is not None and not _ID.fullmatch(expected_id):
            raise ConsentStaleStateError("stale_state")
        try: expected_revision=int(revision)
        except (TypeError,ValueError): raise ConsentStaleStateError("stale_state") from None
        if expected_revision<0 or expected_revision>1_000_000:
            raise ConsentStaleStateError("stale_state")
        return expected_id,expected_revision

    def state(self,user_id: str):
        current=self.repository.latest(user_id,self.policy)
        return {"policy":{
            "consent_type":self.policy.consent_type,"scope":self.policy.scope,
            "version":self.policy.version,"document_hash":self.policy.document_hash,
            "provider":self.policy.provider,"purpose":self.policy.purpose,
            "release_state":self.policy.release_state,"production_active":self.policy.production_active,
            "data_categories":list(self.policy.data_categories),"display_label":self.policy.display_label},
            "current":current,"history":self.repository.history(user_id),
            "accepted_for_current_policy":bool(current and current["status"]=="accepted")}

    def accept(self,user_id: str,*,expected_record_id,expected_revision,now=None):
        expected_id,revision=self.expected_state(expected_record_id,expected_revision)
        try:
            return self.repository.accept(user_id,self.policy,expected_id=expected_id,
                expected_revision=revision,now=int(self.clock() if now is None else now))
        except (ConsentConflictError,ConsentOwnerNotFoundError) as exc:
            raise ConsentStaleStateError(str(exc)) from exc

    def withdraw(self,user_id: str,*,expected_record_id,expected_revision,now=None):
        expected_id,revision=self.expected_state(expected_record_id,expected_revision)
        try:
            return self.repository.withdraw(user_id,self.policy,expected_id=expected_id,
                expected_revision=revision,now=int(self.clock() if now is None else now))
        except (ConsentConflictError,ConsentOwnerNotFoundError) as exc:
            raise ConsentStaleStateError(str(exc)) from exc

    def require_current_acceptance(self,user_id: str,*,session=None):
        row=self.repository.is_active(user_id,self.policy,session=session)
        if row is None: raise ConsentNotActiveError("consent_required")
        return row
