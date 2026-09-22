"""LEGAL-001 consent repository/service semantics without network calls."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from database import create_database, upgrade_database
from domain.consent import AIConsentPolicy
from models import User
from repositories.consent import ConsentRepository
from repositories.privacy import PrivacyRepository
from services.consent import ConsentNotActiveError, ConsentService, ConsentStaleStateError
from services.legal_policy import CURRENT_AI_CONSENT_POLICY

NOW=1780000000

def _policy(**changes):
    values={name:getattr(CURRENT_AI_CONSENT_POLICY,name)
            for name in CURRENT_AI_CONSENT_POLICY.__dataclass_fields__}
    values.update(changes)
    return AIConsentPolicy(**values)

@pytest.fixture()
def consent_env(tmp_path):
    url=f"sqlite:///{tmp_path}/consent.db";upgrade_database(url);db=create_database(url)
    owner,other=str(uuid4()),str(uuid4())
    with db.session() as s,s.begin():
        for uid in (owner,other):
            s.add(User(id=uid,status="active",email_verified_at=NOW,password_hash="test-only",
                       created_at=NOW,updated_at=NOW))
    service=ConsentService(ConsentRepository(db),clock=lambda:NOW)
    yield db,owner,other,service
    db.dispose()

def test_no_consent_accept_withdraw_reaccept_and_version_isolation(consent_env):
    db,owner,other,service=consent_env
    with pytest.raises(ConsentNotActiveError): service.require_current_acceptance(owner)
    first=service.accept(owner,expected_record_id=None,expected_revision=0)
    assert first["status"]=="accepted" and first["cycle"]==1 and first["revision"]==1
    assert service.require_current_acceptance(owner)["id"]==first["id"]
    with pytest.raises(ConsentStaleStateError):
        service.accept(owner,expected_record_id=None,expected_revision=0)
    withdrawn=service.withdraw(owner,expected_record_id=first["id"],expected_revision=1,now=NOW+1)
    assert withdrawn["status"]=="withdrawn" and withdrawn["revision"]==2
    with pytest.raises(ConsentNotActiveError): service.require_current_acceptance(owner)
    with pytest.raises(ConsentStaleStateError):
        service.withdraw(owner,expected_record_id=first["id"],expected_revision=1,now=NOW+2)
    second=service.accept(owner,expected_record_id=first["id"],expected_revision=2,now=NOW+3)
    assert second["id"]!=first["id"] and second["cycle"]==2 and second["status"]=="accepted"
    assert service.repository.history(other)==[]
    with pytest.raises(ConsentNotActiveError):
        ConsentService(ConsentRepository(db),policy=_policy(version="older-policy-v0")).require_current_acceptance(owner)
    with pytest.raises(ConsentNotActiveError):
        ConsentService(ConsentRepository(db),policy=_policy(provider="other")).require_current_acceptance(owner)
    with pytest.raises(ConsentNotActiveError):
        ConsentService(ConsentRepository(db),policy=_policy(purpose="other")).require_current_acceptance(owner)

def test_two_tab_accept_and_withdraw_are_serialized(consent_env):
    _db,owner,_other,service=consent_env
    def accept(_):
        try: return ("ok",service.accept(owner,expected_record_id=None,expected_revision=0)["id"])
        except ConsentStaleStateError: return ("stale",None)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(accept,range(2)))
    assert sorted(x[0] for x in results)==["ok","stale"]
    current=service.state(owner)["current"]
    def withdraw(_):
        try:
            return ("ok",service.withdraw(owner,expected_record_id=current["id"],
                                           expected_revision=current["revision"],now=NOW+10)["revision"])
        except ConsentStaleStateError: return ("stale",None)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(withdraw,range(2)))
    assert sorted(x[0] for x in results)==["ok","stale"]

def test_privacy_export_and_delete_include_owner_consent(consent_env):
    db,owner,other,service=consent_env
    service.accept(owner,expected_record_id=None,expected_revision=0)
    repo=PrivacyRepository(db)
    snapshot,_=repo.export_snapshot(owner,expected_password_hash="test-only")
    assert len(snapshot["ai_consents"])==1 and snapshot["ai_consents"][0]["status"]=="accepted"
    other_snapshot,_=repo.export_snapshot(other,expected_password_hash="test-only")
    assert other_snapshot["ai_consents"]==[]
    counts=repo.delete_account(owner,expected_password_hash="test-only",now=NOW+20)
    assert counts["ai_consents"]==1 and service.repository.history(owner)==[]
