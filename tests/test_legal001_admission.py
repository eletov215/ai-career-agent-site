"""LEGAL-001 admission requires consent and separate reviewed-code activation."""
import os
from types import SimpleNamespace
from uuid import uuid4
import pytest
from database import create_database, upgrade_database
from domain.consent import AIConsentPolicy
from domain.cover_letter import LetterError
from models import User
from repositories.consent import ConsentRepository
from services.ai.letter_admission import LegalLetterAdmission
from services.ai.letter_contract import CONTRACT_VERSION
from services.consent import ConsentService
from services.legal_policy import CURRENT_AI_CONSENT_POLICY

NOW=1780000000

def _env(tmp_path,policy=CURRENT_AI_CONSENT_POLICY):
    url=f"sqlite:///{tmp_path}/{uuid4().hex}.db";upgrade_database(url);db=create_database(url);uid=str(uuid4())
    with db.session() as s,s.begin():
        s.add(User(id=uid,status="active",email_verified_at=NOW,created_at=NOW,updated_at=NOW))
    svc=ConsentService(ConsentRepository(db),policy=policy,clock=lambda:NOW)
    return db,uid,svc,LegalLetterAdmission(svc)

def test_consent_alone_never_opens_draft_policy_or_environment_bypass(tmp_path,monkeypatch):
    db,uid,svc,gate=_env(tmp_path);contract=SimpleNamespace(version=CONTRACT_VERSION)
    try:
        with pytest.raises(LetterError,match="generation_unavailable"):
            gate.check(user_id=uid,letter_id=str(uuid4()),contract=contract,now=NOW)
        consent=svc.accept(uid,expected_record_id=None,expected_revision=0)
        assert svc.require_current_acceptance(uid)["id"]==consent["id"]
        for name in ("AI_ENABLED","AI_SYNTHETIC_ACCESS_ENABLED","AI_LEGAL_APPROVED"):
            monkeypatch.setenv(name,"1")
        with pytest.raises(LetterError,match="generation_unavailable"):
            gate.check(user_id=uid,letter_id=str(uuid4()),contract=contract,now=NOW)
        svc.withdraw(uid,expected_record_id=consent["id"],expected_revision=1,now=NOW+1)
        with pytest.raises(LetterError,match="generation_unavailable"):
            gate.check(user_id=uid,letter_id=str(uuid4()),contract=contract,now=NOW+1)
    finally: db.dispose()

def test_wrong_provider_purpose_or_contract_fail_closed(tmp_path):
    for changes in ({"provider":"other"},{"purpose":"other"}):
        values={name:getattr(CURRENT_AI_CONSENT_POLICY,name) for name in CURRENT_AI_CONSENT_POLICY.__dataclass_fields__}
        values.update(changes);policy=AIConsentPolicy(**values)
        db,uid,svc,gate=_env(tmp_path,policy)
        try:
            svc.accept(uid,expected_record_id=None,expected_revision=0)
            with pytest.raises(LetterError,match="generation_unavailable"):
                gate.check(user_id=uid,letter_id=str(uuid4()),contract=SimpleNamespace(version=CONTRACT_VERSION),now=NOW)
        finally: db.dispose()
    db,uid,svc,gate=_env(tmp_path)
    try:
        svc.accept(uid,expected_record_id=None,expected_revision=0)
        with pytest.raises(LetterError,match="generation_unavailable"):
            gate.check(user_id=uid,letter_id=str(uuid4()),contract=SimpleNamespace(version="wrong"),now=NOW)
    finally: db.dispose()
