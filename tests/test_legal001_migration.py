"""LEGAL-001 additive migration and cascade metadata."""
from uuid import uuid4
from pathlib import Path
from scripts.ai004_m04b_successor import expected_schema_head
from sqlalchemy import inspect, text
from database import CURRENT_REVISION, create_database, current_revision, downgrade_database, upgrade_database
from models import User

def test_0020_to_0021_round_trip_and_owner_cascade(tmp_path):
    url=f"sqlite:///{tmp_path}/legal001.db"
    upgrade_database(url,"20260917_0020")
    db=create_database(url);owner=str(uuid4())
    try:
        with db.session() as s,s.begin():
            s.add(User(id=owner,status="active",email_verified_at=1,created_at=1,updated_at=1))
        upgrade_database(url,"20260922_0021")
        assert current_revision(db.engine)=="20260922_0021"
        # Keep the original LEGAL-001 0021 migration/cascade assertion.
        # Only the later application HEAD advances via reviewed 0024 evidence.
        assert CURRENT_REVISION==expected_schema_head(
            Path(__file__).resolve().parents[1], "20261002_0023"
        )
        inspector=inspect(db.engine)
        assert "ai_consents" in inspector.get_table_names()
        columns={c["name"] for c in inspector.get_columns("ai_consents")}
        assert columns=={"id","user_id","consent_type","scope","policy_version","policy_hash","provider","purpose",
                         "status","cycle","revision","accepted_at","withdrawn_at","created_at","updated_at"}
        indexes={i["name"] for i in inspector.get_indexes("ai_consents")}
        assert {"idx_ai_consents_owner_created","idx_ai_consents_owner_policy","uq_ai_consents_active_policy"}<=indexes
        with db.engine.begin() as conn:
            conn.execute(text("""INSERT INTO ai_consents
                (id,user_id,consent_type,scope,policy_version,policy_hash,provider,purpose,status,cycle,revision,
                 accepted_at,withdrawn_at,created_at,updated_at)
                VALUES (:id,:u,'external_ai_processing','cover_letter_drafting','v','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                        'yandex-alice-ai-llm','cover_letter_proposal_generation','accepted',1,1,1,NULL,1,1)"""),
                {"id":str(uuid4()),"u":owner})
            assert conn.scalar(text("SELECT COUNT(*) FROM ai_consents WHERE user_id=:u"),{"u":owner})==1
        with db.session() as s,s.begin(): s.delete(s.get(User,owner))
        with db.engine.connect() as conn:
            assert conn.scalar(text("SELECT COUNT(*) FROM ai_consents"))==0
    finally:
        db.dispose()
    downgrade_database(url,"20260917_0020")
    db=create_database(url)
    try:
        assert current_revision(db.engine)=="20260917_0020"
        assert "ai_consents" not in inspect(db.engine).get_table_names()
    finally: db.dispose()
