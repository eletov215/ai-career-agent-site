from alembic import command
from sqlalchemy import inspect
from database import alembic_config, create_database, current_revision, downgrade_database, upgrade_database


def test_0021_to_0022_round_trip_without_backfill(tmp_path):
    url=f'sqlite:///{tmp_path}/migration.db';upgrade_database(url,'20260922_0021');db=create_database(url)
    before=set(inspect(db.engine).get_table_names())
    upgrade_database(url,'20261001_0022')
    assert current_revision(db.engine)=='20261001_0022'
    assert set(inspect(db.engine).get_table_names())-before=={
        'saved_vacancy_trackers','saved_vacancy_tracker_events'}
    event_columns={column['name'] for column in inspect(db.engine).get_columns('saved_vacancy_tracker_events')}
    assert 'event_revision' in event_columns
    event_constraints={item['name'] for item in inspect(db.engine).get_unique_constraints(
        'saved_vacancy_tracker_events')}
    assert 'uq_tracker_event_owner_saved_revision' in event_constraints
    upgrade_database(url)
    command.check(alembic_config(url))
    downgrade_database(url,'20261001_0022')
    downgrade_database(url,'20260922_0021')
    assert set(inspect(db.engine).get_table_names())==before
    db.dispose()
