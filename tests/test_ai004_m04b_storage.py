"""M04B: disposable-DB only tests; no AI provider, Neon or production routes."""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pytest
from sqlalchemy import delete, func, select

from database import create_database, upgrade_database
from domain.ai import PROVIDER, REAL_DATA_SUPPORTED
from domain.saved_vacancy import SNAPSHOT_VERSION, canonical_json as snapshot_json, fingerprint
from models import ResumeDraft, ResumeVersion, SavedVacancy, User
from models.ai import (
    AIBudgetBucket, AIProviderState, AIRuntimePolicy, AIRequestLease,
    AIUsageEvent,
)
from models.user_match import UserMatchCache, UserMatchReport
from repositories.ai import AIRepository
from repositories.privacy import PrivacyRepository
from repositories.user_match import (
    UserMatchRepository, UserMatchStorageError,
    report_export_view,
)
from services.ai.policy import DEFAULT_POLICY
from services.matching_validation import validate_classification
from services.matching_contract import CLASSIFICATION_VERSION
from services.privacy import PrivacyService

SECRET = b"m04b-disposable-tests-hmac-not-a-production-secret-00001"
NOW = 1_780_000_000


def seed(db, owner=None, *, suffix="a"):
    owner = owner or str(uuid.uuid4())
    draft_id, version_id, saved_id = (str(uuid.uuid4()) for _ in range(3))
    resume = {
        "schemaVersion": 1, "index": 0,
        "answers": {"role": "Python developer", "skills": "Python, SQL"},
        "messages": [], "photoAssetId": None,
    }
    canonical_resume = json.dumps(resume, ensure_ascii=False,
                                  sort_keys=True, separators=(",", ":"))
    src = {
        "title": "Backend engineer", "company": "Synthetic employer",
        "location": "", "description": "A role",
        "requirements": "Python; Nice to have SQL",
        "work_format": "remote", "employment_code": "full",
        "experience_code": "unknown",
        "salary_from": None, "salary_to": None,
        "currency": "RUB", "schedule": "",
        "employment": "", "experience": "", "published_at": "",
        "source_records": [{
            "source": "hh", "source_title": "HeadHunter",
            "external_id": "synthetic-" + suffix,
            "url": "https://hh.ru/vacancy/" + suffix,
            "source_status": "active",
        }],
    }
    from services.saved_vacancy_snapshot import build_snapshot
    snapshot = build_snapshot(src)
    with db.session() as s, s.begin():
        s.add(User(
            id=owner, email=f"{owner}@example.test",
            normalized_email=f"{owner}@example.test",
            display_name="Synthetic", status="active",
            email_verified_at=NOW, password_hash="safe-fake-password-hash",
            password_changed_at=NOW, last_login_at=NOW,
            created_at=NOW, updated_at=NOW,
        ))
        # SQLAlchemy has no direct User relationship to every feature model;
        # flush the parent explicitly before FK-bound synthetic fixture rows.
        s.flush()
        s.add(ResumeDraft(
            id=draft_id, user_id=owner,
            schema_version=1, revision=1,
            title="Synthetic resume", state_json=canonical_resume,
            content_hash=hashlib.sha256(canonical_resume.encode()).hexdigest(),
            completion_percent=100, profile_version=None,
            created_at=NOW, updated_at=NOW,
        ))
        s.flush()
        s.add(ResumeVersion(
            id=version_id, draft_id=draft_id, schema_version=1,
            version=1, draft_revision=1,
            snapshot_json=canonical_resume,
            content_hash=hashlib.sha256(canonical_resume.encode()).hexdigest(),
            reason="checkpoint", restored_from_version=None, created_at=NOW,
        ))
        s.add(SavedVacancy(
            id=saved_id, user_id=owner,
            snapshot_json=snapshot_json(snapshot),
            snapshot_hash=fingerprint(snapshot),
            snapshot_version=SNAPSHOT_VERSION,
            title=snapshot["title"], company=snapshot["company"],
            location=snapshot["location"], search_text="synthetic backend engineer",
            note="private author note", revision=1,
            created_at=NOW, updated_at=NOW,
        ))
    return {"owner": owner, "draft": draft_id, "version": version_id,
            "saved": saved_id, "snapshot": snapshot}


@pytest.fixture()
def env(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'm04b.db'}"
    upgrade_database(db_url)
    db = create_database(db_url)
    first = seed(db, suffix="first")
    second = seed(db, suffix="second")
    yield db, first, second
    db.dispose()


def repo(db):
    return UserMatchRepository(db, fingerprint_key=SECRET)


def claim(store, source, *, nonce="click-0001", now=NOW):
    return store.claim_saved(
        user_id=source["owner"],
        resume_version_id=source["version"],
        saved_vacancy_id=source["saved"],
        owner_action_nonce=nonce, now=now, lease_seconds=300,
    )


def validated(db, source):
    with db.session() as s:
        contract, _, _ = repo(db)._source(
            s, source["owner"], source["version"], source["saved"],
        )
    raw = json.dumps({
        "contract_version": CLASSIFICATION_VERSION,
        "source_hash": contract.source_hash,
        "classifications": [
            {"requirement_id": "req-001", "status": "matched",
             "candidate_evidence": [{"id": "resume.skills", "quote": "Python"}]},
            {"requirement_id": "req-002", "status": "matched",
             "candidate_evidence": [{"id": "resume.skills", "quote": "SQL"}]},
        ],
    })
    return validate_classification(raw, contract)


def seed_ledger(db, source, claim_id, *, now=NOW):
    # Direct synthetic database fixture. No AIRepository.admit() and no API call.
    with db.session() as s:
        c = s.scalar(select(UserMatchCache).where(UserMatchCache.id == claim_id))
        key_hash, request_hash = c.operation_hash, c.request_hash
    event_id = str(uuid.uuid4())
    from datetime import datetime, timezone
    day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
    month = day[:7]
    policy = {**DEFAULT_POLICY, "enabled": True, "kill_switch": False}
    with db.session() as s, s.begin():
        # The initial migration may seed a disabled policy; ONLY disposable
        # synthetic tests switch it on to exercise the ledger callback.
        runtime_policy = s.get(AIRuntimePolicy, 1)
        if runtime_policy is None:
            s.add(AIRuntimePolicy(
                id=1, version=1, policy_json=json.dumps(policy),
                updated_at=now,
            ))
        else:
            runtime_policy.policy_json = json.dumps(policy)
            runtime_policy.updated_at = now
        if s.get(AIProviderState, PROVIDER) is None:
            s.add(AIProviderState(
                provider=PROVIDER, failures=0, open_until=0,
                probe_request_id=None, probe_until=0,
            ))
        s.add(AIUsageEvent(
            id=event_id, user_id=source["owner"],
            idempotency_hash=key_hash, request_hash=request_hash,
            task="vacancy_match", language="en",
            fixture_id="general-vacancy-match", prompt_version="grounded-v2.6.1",
            policy_version=1, input_rate=1, output_rate=1,
            day=day, month=month,
            status="reserved", reason="admitted",
            reserved_microrub=100, charged_microrub=100,
            cost_uncertain=True, attempts=1,
            input_tokens=0, output_tokens=0,
            commercial_reserved=False, commercial_action_consumed=False,
            created_at=now, updated_at=now, lease_expires_at=now + 300,
        ))
        s.add(AIRequestLease(id=event_id, expires_at=now + 300))
        for bucket_id, user_id, period in (
            (f"user:{source['owner']}:day:{day}", source["owner"], day),
            (f"global:day:{day}", None, day),
            (f"global:month:{month}", None, month),
            (f"user:{source['owner']}:action:vacancy_match:{month}",
             source["owner"], month),
        ):
            if s.get(AIBudgetBucket, bucket_id) is None:
                s.add(AIBudgetBucket(
                    id=bucket_id, user_id=user_id, period=period,
                    spent_microrub=100 if "action" not in bucket_id else 0,
                    requests=1, successes=0,
                ))
    return event_id


def settle(db, source, claim_id, response, *, now=NOW + 20):
    event_id = seed_ledger(db, source, claim_id)
    storage = repo(db)
    def on_success(session, event):
        storage.settle_ready_in_session(
            session, claim_id=claim_id, event=event,
            validated=response, now=now,
        )
    accepted = AIRepository(db).settle(
        event_id, status="succeeded", reason="ok",
        cost=0, uncertain=False, input_tokens=0, output_tokens=0,
        provider_failed=False, now=now, on_success=on_success,
    )
    return event_id, accepted


def test_claim_is_owner_bound_deduplicated_and_keeps_private_material_out(env):
    db, first, second = env
    storage = repo(db)
    pending = claim(storage, first)
    again = claim(storage, first, nonce="click-0002")
    assert pending == again and pending["state"] == "pending"
    assert storage.load_saved(
        user_id=first["owner"], resume_version_id=first["version"],
        saved_vacancy_id=first["saved"], now=NOW,
    ) == pending
    assert claim(storage, second)["id"] != pending["id"]
    with pytest.raises(UserMatchStorageError, match="^not_found$"):
        storage.claim_saved(
            user_id=second["owner"],
            resume_version_id=first["version"],
            saved_vacancy_id=first["saved"],
            owner_action_nonce="click-0003", now=NOW,
        )
    with pytest.raises(UserMatchStorageError, match="^not_found$"):
        storage.load_saved(
            user_id=first["owner"], resume_version_id=second["version"],
            saved_vacancy_id=first["saved"], now=NOW,
        )
    raw = json.dumps(pending)
    assert "Python" not in raw and "private author note" not in raw
    assert "cache_key_hash" not in raw and "operation_hash" not in raw
    assert REAL_DATA_SUPPORTED is False


def test_atomic_ledger_success_creates_one_signed_report_and_ready_cache(env):
    db, first, _ = env
    storage = repo(db)
    pending = claim(storage, first)
    output = validated(db, first)
    event_id, accepted = settle(db, first, pending["id"], output)
    assert accepted is True
    read = storage.load_saved(
        user_id=first["owner"], resume_version_id=first["version"],
        saved_vacancy_id=first["saved"], now=NOW + 21,
    )
    assert read["state"] == "ready"
    assert read["report"]["result"]["summary"]["score_percent"] == 100
    assert read["report"]["result"]["summary"]["policy_version"] == "weighted-evidence-v1"
    assert read["report"]["result"]["requirements"][0]["candidate_evidence"][0]["quote"] == "Python"
    assert claim(storage, first, nonce="click-replay")["id"] == pending["id"]
    with db.session() as s:
        row = s.scalar(select(UserMatchReport).where(UserMatchReport.user_id == first["owner"]))
        assert row is not None and row.usage_event_id == event_id
        assert len(row.result_seal) == len(row.result_hash) == 64
        assert s.get(AIUsageEvent, event_id).status == "succeeded"
        assert s.scalar(select(func.count()).select_from(UserMatchReport)) == 1
        assert "private author note" not in row.result_json
        assert "Synthetic employer" not in row.result_json


def test_bad_report_rolls_back_report_and_ledger_success_atomically(env):
    db, first, _ = env
    storage = repo(db)
    pending = claim(storage, first)
    output = validated(db, first)
    output["summary"]["score_percent"] = 999
    event_id = seed_ledger(db, first, pending["id"])
    with pytest.raises(UserMatchStorageError, match="^invalid_saved_report$"):
        AIRepository(db).settle(
            event_id, status="succeeded", reason="ok", cost=0,
            uncertain=False, input_tokens=0, output_tokens=0,
            provider_failed=False, now=NOW + 10,
            on_success=lambda s, e: storage.settle_ready_in_session(
                s, claim_id=pending["id"], event=e, validated=output, now=NOW + 10,
            ),
        )
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(UserMatchReport)) == 0
        assert s.get(AIUsageEvent, event_id).status == "reserved"
        assert s.get(UserMatchCache, pending["id"]).state == "pending"


def test_expired_and_uncertain_claims_never_auto_retry(env):
    db, first, _ = env
    storage = repo(db)
    original = claim(storage, first)
    expired = claim(storage, first, now=NOW + 301, nonce="click-different")
    assert expired["id"] == original["id"]
    assert expired["state"] == "unknown"
    assert claim(storage, first, now=NOW + 302, nonce="click-other")["state"] == "unknown"
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(UserMatchCache).where(
            UserMatchCache.user_id == first["owner"],
        )) == 1


def test_closed_failed_usage_keeps_cache_blocked_and_cannot_be_overwritten(env):
    db, first, _ = env
    storage = repo(db)
    pending = claim(storage, first)
    event_id = seed_ledger(db, first, pending["id"])
    with db.session() as s, s.begin():
        e = s.get(AIUsageEvent, event_id)
        e.status = "failed"
        e.cost_uncertain = False
    closed = storage.close_claim(
        user_id=first["owner"], claim_id=pending["id"], now=NOW + 5,
    )
    assert closed["state"] == "failed"
    assert claim(storage, first, nonce="different-click")["state"] == "failed"
    assert storage.close_claim(
        user_id=first["owner"], claim_id=pending["id"], now=NOW + 6,
    )["state"] == "failed"


def test_corrupted_report_is_not_served_even_if_sha256_is_recomputed(env):
    db, first, _ = env
    storage = repo(db)
    pending = claim(storage, first)
    settle(db, first, pending["id"], validated(db, first))
    with db.session() as s, s.begin():
        row = s.scalar(select(UserMatchReport).where(
            UserMatchReport.user_id == first["owner"],
        ))
        content = json.loads(row.result_json)
        content["requirements"][0]["candidate_evidence"][0]["quote"] = "invented"
        row.result_json = json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        row.result_hash = hashlib.sha256(row.result_json.encode()).hexdigest()
    with pytest.raises(UserMatchStorageError, match="^invalid_saved_report$"):
        storage.load_saved(
            user_id=first["owner"], resume_version_id=first["version"],
            saved_vacancy_id=first["saved"], now=NOW + 30,
        )


def test_account_export_counts_and_owner_delete_cascade(env, tmp_path):
    from tests.test_privacy_service import _settings
    db, first, _ = env
    storage = repo(db)
    pending = claim(storage, first)
    settle(db, first, pending["id"], validated(db, first))
    service = PrivacyService(PrivacyRepository(db), _settings(tmp_path))
    artifact = service.export_user_data(
        first["owner"], expected_password_hash="safe-fake-password-hash",
        now=NOW + 30,
    )
    with zipfile.ZipFile(BytesIO(artifact.content)) as archive:
        obj = json.loads(archive.read("data.json"))
        manifest = json.loads(archive.read("manifest.json"))
    assert len(obj["user_match_reports"]) == 1
    assert len(obj["user_match_cache"]) == 1
    assert obj["user_match_reports"][0]["result"]["summary"]["score_percent"] == 100
    assert manifest["counts"]["user_match_reports"] == 1
    assert manifest["counts"]["user_match_cache"] == 1
    for item in obj["user_match_cache"]:
        assert "operation_hash" not in item and "cache_key_hash" not in item
    deleted = service.delete_account(
        first["owner"], expected_password_hash="safe-fake-password-hash",
        now=NOW + 40,
    )
    assert deleted["user_match_reports"] == 1 and deleted["user_match_cache"] == 1
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(UserMatchReport).where(
            UserMatchReport.user_id == first["owner"],
        )) == 0
        assert s.scalar(select(func.count()).select_from(UserMatchCache).where(
            UserMatchCache.user_id == first["owner"],
        )) == 0


def test_saved_vacancy_delete_purges_derived_cache_and_report(env):
    db, first, _ = env
    storage = repo(db)
    pending = claim(storage, first)
    settle(db, first, pending["id"], validated(db, first))
    with db.session() as s, s.begin():
        s.execute(delete(SavedVacancy).where(SavedVacancy.id == first["saved"]))
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(UserMatchReport).where(
            UserMatchReport.user_id == first["owner"],
        )) == 0
        assert s.scalar(select(func.count()).select_from(UserMatchCache).where(
            UserMatchCache.user_id == first["owner"],
        )) == 0


def test_resume_version_delete_purges_derived_cache_and_report(env):
    db, first, _ = env
    storage = repo(db)
    pending = claim(storage, first)
    settle(db, first, pending["id"], validated(db, first))
    with db.session() as s, s.begin():
        s.execute(delete(ResumeVersion).where(ResumeVersion.id == first["version"]))
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(UserMatchReport)) == 0
        assert s.scalar(select(func.count()).select_from(UserMatchCache).where(
            UserMatchCache.user_id == first["owner"],
        )) == 0


def test_owner_scoped_deletion_requires_matching_result_hash(env):
    db, first, second = env
    storage = repo(db)
    pending = claim(storage, first)
    settle(db, first, pending["id"], validated(db, first))
    with db.session() as s:
        report = s.scalar(select(UserMatchReport).where(
            UserMatchReport.user_id == first["owner"],
        ))
        report_id, result_hash = report.id, report.result_hash
    with pytest.raises(UserMatchStorageError, match="^not_found$"):
        storage.delete_report(
            user_id=second["owner"], report_id=report_id, result_hash=result_hash,
        )
    with pytest.raises(UserMatchStorageError, match="^stale_report$"):
        storage.delete_report(
            user_id=first["owner"], report_id=report_id, result_hash="0" * 64,
        )
    storage.delete_report(
        user_id=first["owner"], report_id=report_id, result_hash=result_hash,
    )
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(UserMatchReport).where(
            UserMatchReport.user_id == first["owner"],
        )) == 0
        assert s.scalar(select(func.count()).select_from(UserMatchCache).where(
            UserMatchCache.user_id == first["owner"],
        )) == 0


def test_concurrent_duplicate_claims_have_one_owner_scoped_pending_row(env):
    db, first, _ = env
    storage = repo(db)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(
            lambda n: claim(storage, first, nonce=f"click-00{n}"),
            range(4),
        ))
    assert {item["id"] for item in outcomes} == {outcomes[0]["id"]}
    with db.session() as s:
        assert s.scalar(select(func.count()).select_from(UserMatchCache).where(
            UserMatchCache.user_id == first["owner"],
        )) == 1


def test_untrusted_source_hash_and_unverified_owner_fail_closed(env):
    db, first, other = env
    storage = repo(db)
    with db.session() as s, s.begin():
        row = s.get(ResumeVersion, first["version"])
        row.snapshot_json = '{"schemaVersion":1,"answers":{"skills":"FAKE"}}'
    with pytest.raises(UserMatchStorageError, match="^invalid_source$"):
        claim(storage, first)
    with pytest.raises(UserMatchStorageError, match="^not_found$"):
        storage.claim_saved(
            user_id=first["owner"], resume_version_id=first["version"],
            saved_vacancy_id=other["saved"],
            owner_action_nonce="click-0099", now=NOW,
        )


@pytest.mark.skipif(not os.environ.get("POSTGRES_TEST_URL"),
                    reason="Disposable PostgreSQL service required in CI")
def test_disposable_postgres_owner_lock_concurrency_and_cascade():
    db_url = os.environ["POSTGRES_TEST_URL"]
    upgrade_database(db_url)
    db = create_database(db_url)
    src = seed(db, suffix="pg-owner-lock")
    try:
        storage = repo(db)
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows = list(pool.map(
                lambda n: claim(storage, src, nonce=f"pgclick-{n:04d}"),
                range(3),
            ))
        assert len({r["id"] for r in rows}) == 1
        settle(db, src, rows[0]["id"], validated(db, src))
        db.dispose()
        assert repo(db).load_saved(
            user_id=src["owner"], resume_version_id=src["version"],
            saved_vacancy_id=src["saved"], now=NOW + 50,
        )["state"] == "ready"
        with db.session() as s, s.begin():
            s.execute(delete(User).where(User.id == src["owner"]))
        with db.session() as s:
            assert s.scalar(select(func.count()).select_from(UserMatchCache).where(
                UserMatchCache.user_id == src["owner"],
            )) == 0
            assert s.scalar(select(func.count()).select_from(UserMatchReport).where(
                UserMatchReport.user_id == src["owner"],
            )) == 0
    finally:
        with db.session() as s, s.begin():
            s.execute(delete(User).where(User.id == src["owner"]))
        db.dispose()
