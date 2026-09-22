"""LEGAL-001 consent business logic."""
from __future__ import annotations
import re
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

_ID=re.compile(r"^[0-9a-fA-F-]{36}$")

class ConsentService:
    def __init__(self, repository: ConsentRepository, *, policy: AIConsentPolicy=CURRENT_AI_CONSENT_POLICY, clock=time.time):
        self.repository=repository;self.policy=policy;self.clock=clock

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
