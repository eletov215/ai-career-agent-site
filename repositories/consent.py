"""Repository boundary for versioned LEGAL-001 owner consent."""
from __future__ import annotations
import uuid
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from domain.consent import AIConsentPolicy
from models.consent import AIConsent
from models.user import User
from repositories.base import RepositoryBase

class ConsentConflictError(RuntimeError):
    pass

class ConsentOwnerNotFoundError(LookupError):
    pass

def consent_view(row: AIConsent) -> dict[str, object]:
    return {
        "id": row.id, "consent_type": row.consent_type, "scope": row.scope,
        "policy_version": row.policy_version, "policy_hash": row.policy_hash,
        "provider": row.provider, "purpose": row.purpose, "status": row.status,
        "cycle": row.cycle, "revision": row.revision, "accepted_at": row.accepted_at,
        "withdrawn_at": row.withdrawn_at, "created_at": row.created_at, "updated_at": row.updated_at,
    }

class ConsentRepository(RepositoryBase):
    @staticmethod
    def _policy_conditions(policy: AIConsentPolicy):
        return (
            AIConsent.consent_type == policy.consent_type, AIConsent.scope == policy.scope,
            AIConsent.policy_version == policy.version, AIConsent.policy_hash == policy.document_hash,
            AIConsent.provider == policy.provider, AIConsent.purpose == policy.purpose,
        )

    def _latest_in_session(self, session: Session, user_id: str, policy: AIConsentPolicy, *, lock: bool=False):
        statement=(select(AIConsent)
            .where(AIConsent.user_id == str(user_id), *self._policy_conditions(policy))
            .order_by(AIConsent.cycle.desc()).limit(1))
        if lock and self.engine.dialect.name == "postgresql":
            statement=statement.with_for_update()
        return session.scalar(statement)

    def latest(self, user_id: str, policy: AIConsentPolicy):
        with self.session() as session:
            row=self._latest_in_session(session,user_id,policy)
            return consent_view(row) if row is not None else None

    def history(self, user_id: str, *, limit: int=200):
        bounded=max(1,min(int(limit),500))
        with self.session() as session:
            rows=session.scalars(select(AIConsent).where(AIConsent.user_id==str(user_id))
                .order_by(AIConsent.created_at.desc(),AIConsent.cycle.desc(),AIConsent.id.desc())
                .limit(bounded)).all()
            return [consent_view(row) for row in rows]

    def is_active(self, user_id: str, policy: AIConsentPolicy, *, session: Session | None=None):
        if session is not None:
            row=self._latest_in_session(session,user_id,policy,lock=True)
            return consent_view(row) if row is not None and row.status=="accepted" else None
        with self.session() as owned:
            row=self._latest_in_session(owned,user_id,policy)
            return consent_view(row) if row is not None and row.status=="accepted" else None

    @staticmethod
    def _expected_matches(row, expected_id, expected_revision):
        if row is None:
            return expected_id is None and expected_revision==0
        return row.id==expected_id and row.revision==expected_revision

    def _lock_owner(self, session: Session, user_id: str):
        statement=select(User.id).where(User.id==str(user_id))
        if self.engine.dialect.name=="postgresql":
            statement=statement.with_for_update()
        if session.scalar(statement) is None:
            raise ConsentOwnerNotFoundError("owner_not_found")

    def accept(self, user_id: str, policy: AIConsentPolicy, *, expected_id, expected_revision: int, now: int):
        with self.session() as session:
            try:
                if self.engine.dialect.name=="sqlite":
                    session.execute(text("BEGIN IMMEDIATE"))
                self._lock_owner(session,user_id)
                current=self._latest_in_session(session,user_id,policy,lock=True)
                if not self._expected_matches(current,expected_id,expected_revision):
                    raise ConsentConflictError("stale_state")
                if current is not None and current.status=="accepted":
                    raise ConsentConflictError("already_accepted")
                row=AIConsent(
                    id=str(uuid.uuid4()),user_id=str(user_id),consent_type=policy.consent_type,
                    scope=policy.scope,policy_version=policy.version,policy_hash=policy.document_hash,
                    provider=policy.provider,purpose=policy.purpose,status="accepted",
                    cycle=1 if current is None else current.cycle+1,revision=1,
                    accepted_at=int(now),withdrawn_at=None,created_at=int(now),updated_at=int(now))
                session.add(row);session.flush();result=consent_view(row);session.commit();return result
            except IntegrityError as exc:
                session.rollback();raise ConsentConflictError("stale_state") from exc
            except BaseException:
                session.rollback();raise

    def withdraw(self, user_id: str, policy: AIConsentPolicy, *, expected_id, expected_revision: int, now: int):
        with self.session() as session:
            try:
                if self.engine.dialect.name=="sqlite":
                    session.execute(text("BEGIN IMMEDIATE"))
                self._lock_owner(session,user_id)
                current=self._latest_in_session(session,user_id,policy,lock=True)
                if not self._expected_matches(current,expected_id,expected_revision):
                    raise ConsentConflictError("stale_state")
                if current is None or current.status!="accepted":
                    raise ConsentConflictError("not_active")
                current.status="withdrawn";current.withdrawn_at=int(now);current.updated_at=int(now);current.revision+=1
                session.flush();result=consent_view(current);session.commit();return result
            except BaseException:
                session.rollback();raise
