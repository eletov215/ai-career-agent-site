"""M04B additive 0024 migration tests on disposable SQLite, never Neon."""
from __future__ import annotations

from alembic import command
from sqlalchemy import inspect, select

from database import (
    CURRENT_REVISION, alembic_config, create_database,
    current_revision, downgrade_database, upgrade_database,
)
from models import User, VacancyMatchReport, VacancyMatchSeries


def test_0023_to_0024_roundtrip_is_additive_and_old_ai004_history_survives(tmp_path):
    url = f"sqlite:///{tmp_path / 'm04b-migration.db'}"
    upgrade_database(url, "20261002_0023")
    db = create_database(url)
    before = set(inspect(db.engine).get_table_names())
    assert "vacancy_match_reports" in before
    assert "vacancy_match_series" in before
    upgrade_database(url, "20261009_0024")
    assert current_revision(db.engine) == "20261009_0024"
    inspector = inspect(db.engine)
    assert set(inspector.get_table_names()) - before == {
        "user_match_reports", "user_match_cache",
    }
    report_uniques = {
        row["name"] for row in inspector.get_unique_constraints("user_match_reports")
    }
    cache_uniques = {
        row["name"] for row in inspector.get_unique_constraints("user_match_cache")
    }
    assert {"uq_user_match_report_owner_key",
            "uq_user_match_report_owner_usage",
            "uq_user_match_report_id_owner"} <= report_uniques
    assert "uq_user_match_cache_owner_key" in cache_uniques
    cache_fks = inspector.get_foreign_keys("user_match_cache")
    assert any(
        fk["referred_table"] == "user_match_reports"
        and fk["constrained_columns"] == ["report_id", "user_id"]
        for fk in cache_fks
    )
    assert any(
        fk["referred_table"] == "saved_vacancies"
        and fk["constrained_columns"] == ["saved_vacancy_id", "user_id"]
        for fk in cache_fks
    )
    upgrade_database(url, "20261009_0024")
    command.check(alembic_config(url))

    downgrade_database(url, "20261002_0023")
    assert current_revision(db.engine) == "20261002_0023"
    assert set(inspect(db.engine).get_table_names()) == before
    with db.session() as session:
        # Historical fixture AI-004 tables remain accessible after rollback.
        assert session.execute(select(VacancyMatchSeries)).all() == []
        assert session.execute(select(VacancyMatchReport)).all() == []

    upgrade_database(url)
    assert current_revision(db.engine) == CURRENT_REVISION == "20261009_0024"
    command.check(alembic_config(url))
    db.dispose()


def test_new_models_are_registered_but_no_production_admission_enabled(tmp_path):
    from domain.ai import REAL_DATA_SUPPORTED
    from models import Base, UserMatchCache, UserMatchReport
    assert REAL_DATA_SUPPORTED is False
    assert "user_match_cache" in Base.metadata.tables
    assert "user_match_reports" in Base.metadata.tables
    assert UserMatchCache.__tablename__ != "vacancy_match_reports"
    assert UserMatchReport.__tablename__ != "vacancy_match_reports"
