from alembic import command
from sqlalchemy import inspect
from database import CURRENT_REVISION, alembic_config, create_database, current_revision, upgrade_database

def test_0022_to_0023_round_trip_without_backfill(tmp_path):
    url=f'sqlite:///{tmp_path}/migration.db'; upgrade_database(url,'20261001_0022'); db=create_database(url)
    before=set(inspect(db.engine).get_table_names()); upgrade_database(url,'20261002_0023')
    assert current_revision(db.engine)=='20261002_0023'
    assert set(inspect(db.engine).get_table_names())-before=={'notification_preferences','saved_vacancy_reminders'}
    assert {x['name'] for x in inspect(db.engine).get_unique_constraints('saved_vacancy_reminders')} >= {'uq_reminder_owner_saved'}
    # The accepted 0023 state is asserted above. An Alembic drift check
    # is meaningful only at the unique current runtime head (now 0024).
    upgrade_database(url)
    assert current_revision(db.engine)==CURRENT_REVISION
    command.check(alembic_config(url))
    command.downgrade(alembic_config(url),'20261001_0022')
    assert current_revision(db.engine)=='20261001_0022'
    assert not ({'notification_preferences','saved_vacancy_reminders'} & set(inspect(db.engine).get_table_names()))
