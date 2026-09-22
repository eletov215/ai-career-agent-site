"""LEGAL-001 signed forms and consent-cycle binding; isolated/fake transport only."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4
import pytest
from domain.cover_letter import LetterError
from services.ai.letter_contract import CONTRACT_VERSION
from services.legal_policy import CURRENT_AI_CONSENT_POLICY
from services.consent import ConsentStaleStateError
from tests.test_legal001_service import consent_env, NOW
from tests.test_legal001_admission import _env
from tests.test_job001_service import job_env
from tests.test_ai005_service import letters
from tests.test_ai005_live_runtime import live, run, events, NOW as AI_NOW


@pytest.mark.parametrize("changes", [
    {"version": "new-version"}, {"document_hash": "b" * 64},
    {"provider": "other"}, {"purpose": "other"}, {"scope": "other"},
    {"release_state": "ACTIVE"}, {"display_label": "changed disclosure"},
])
def test_empty_form_bound_to_exact_displayed_policy(consent_env, changes):
    from dataclasses import replace
    _db, owner, _other, service = consent_env
    token = service.issue_form_token(owner, None, signing_key="test-form-key")
    service.policy = replace(service.policy, **changes)
    with pytest.raises(ConsentStaleStateError):
        service.validate_form_token(owner, token, action="accept", expected_record_id=None,
                                    expected_revision=0, signing_key="test-form-key")
    assert service.repository.history(owner) == []


def test_form_expiry_wrong_owner_action_revision_tampering_and_fresh_cycle(consent_env):
    _db, owner, other, service = consent_env
    def verify(token, **changes):
        args = dict(action="accept", expected_record_id=None, expected_revision=0,
                    signing_key="test-form-key")
        args.update(changes)
        return service.validate_form_token(owner, token, **args)
    token = service.issue_form_token(owner, None, signing_key="test-form-key")
    verify(token)
    with pytest.raises(ConsentStaleStateError):
        service.validate_form_token(other, token, action="accept", expected_record_id=None,
                                    expected_revision=0, signing_key="test-form-key")
    for change in ({"action": "withdraw"}, {"expected_revision": 1}, {"signing_key": "other-key"}):
        with pytest.raises(ConsentStaleStateError): verify(token, **change)
    for bad in (None, "", token + "x", "0." + "a" * 64, "9" * 9000):
        with pytest.raises(ConsentStaleStateError): verify(bad)
    service.clock = lambda: NOW + 900
    with pytest.raises(ConsentStaleStateError): verify(token)
    service.clock = lambda: NOW
    accepted = service.accept(owner, expected_record_id=None, expected_revision=0)
    withdrawal = service.issue_form_token(owner, accepted, signing_key="test-form-key")
    service.validate_form_token(owner, withdrawal, action="withdraw", expected_record_id=accepted["id"],
                                expected_revision=1, signing_key="test-form-key")
    service.withdraw(owner, expected_record_id=accepted["id"], expected_revision=1)
    with pytest.raises(ConsentStaleStateError):
        service.accept(owner, expected_record_id=None, expected_revision=0)



@pytest.mark.parametrize('changes', [
    {'provider':'other'}, {'purpose':'other'}, {'scope':'other'}, {'consent_type':'other'},
])
def test_active_test_policy_still_rejects_wrong_contract_scope(tmp_path,monkeypatch,changes):
    from dataclasses import replace
    import services.ai.letter_admission as admission_module
    policy=replace(CURRENT_AI_CONSENT_POLICY,release_state='ACTIVE',**changes)
    db,uid,svc,gate=_env(tmp_path,policy)
    monkeypatch.setattr(admission_module,'REAL_DATA_SUPPORTED',True)
    try:
        svc.accept(uid,expected_record_id=None,expected_revision=0)
        with pytest.raises(LetterError,match='generation_unavailable'):
            gate.check(user_id=uid,letter_id=str(uuid4()),contract=SimpleNamespace(version=CONTRACT_VERSION),now=NOW)
    finally: db.dispose()


def test_two_gates_independent_in_synthetic_test_only(tmp_path,monkeypatch):
    from dataclasses import replace
    import services.ai.letter_admission as admission_module
    db,uid,svc,gate=_env(tmp_path,replace(CURRENT_AI_CONSENT_POLICY,release_state='ACTIVE'))
    contract=SimpleNamespace(version=CONTRACT_VERSION)
    args=dict(user_id=uid,letter_id=str(uuid4()),contract=contract,now=NOW)
    try:
        accepted=svc.accept(uid,expected_record_id=None,expected_revision=0)
        # Code product boundary independently blocks even this injected ACTIVE policy.
        with pytest.raises(LetterError): gate.check(**args)
        monkeypatch.setattr(admission_module,'REAL_DATA_SUPPORTED',True)
        assert accepted['id'] in gate.check(**args)
        with pytest.raises(LetterError): gate.check(**{**args,'user_id':str(uuid4())})
        svc.withdraw(uid,expected_record_id=accepted['id'],expected_revision=1,now=NOW+1)
        with pytest.raises(LetterError): gate.check(**args)
        svc.accept(uid,expected_record_id=accepted['id'],expected_revision=2,now=NOW+2)
        assert accepted['id'] not in gate.check(**args)
    finally: db.dispose()



@pytest.mark.parametrize('moment,reaccept', [('before_dispatch',True),('during_provider',True),('during_provider',False)])
def test_legal_consent_cycle_pinned_to_preview_and_result(live,monkeypatch,moment,reaccept):
    # Isolated synthetic fixture and StubTransport only; never deployment flags.
    from repositories.consent import ConsentRepository
    from services.consent import ConsentService
    from services.legal_policy import CURRENT_AI_CONSENT_POLICY
    from services.ai.letter_admission import LegalLetterAdmission
    import services.ai.letter_admission as admission_module
    x=live
    service=ConsentService(ConsentRepository(x.e.db),
        policy=replace(CURRENT_AI_CONSENT_POLICY,release_state='ACTIVE'),clock=lambda:AI_NOW)
    consent=service.accept(x.e.owner,expected_record_id=None,expected_revision=0)
    monkeypatch.setattr(admission_module,'REAL_DATA_SUPPORTED',True)
    x.generator.admission=LegalLetterAdmission(service)
    x.preview=x.generator.preview(x.e.owner,x.record['id'],x.record['revision'],
                                  'en','short','professional',['profile.summary'])
    def revoke():
        service.withdraw(x.e.owner,expected_record_id=consent['id'],expected_revision=1)
        if reaccept:
            service.accept(x.e.owner,expected_record_id=consent['id'],expected_revision=2)
    if moment=='before_dispatch':
        revoke()
        with pytest.raises(LetterError,match='generation_unavailable'):run(x)
        assert not x.transport.calls and not events(x)
    else:
        x.transport.before=revoke
        result=run(x)
        assert result['status']=='manual' and result['reason']=='result_not_delivered'
        assert len(x.transport.calls)==1
        event=events(x)[0]
        assert event.status=='failed' and event.charged_microrub==860000
    assert not x.e.svc.get(x.e.owner,x.record['id'])['proposals']
