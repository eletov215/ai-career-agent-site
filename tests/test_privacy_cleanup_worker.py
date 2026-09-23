"""LEGAL-OPS-01: cold-start, concurrent and failed heartbeat regression tests.

All databases, retention operations, clocks and logging setup are synthetic.
No provider, application user or production filesystem is accessed.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from pathlib import Path
import stat
import threading
from types import SimpleNamespace

import pytest

from scripts import privacy_cleanup_worker as worker


@pytest.mark.parametrize('status', ['ok', 'lock_busy', 'error'])
def test_heartbeat_creates_missing_parent_and_keeps_wire_contract(tmp_path, status):
    settings = SimpleNamespace(data_dir=tmp_path / 'fresh-instance' / 'data')
    worker._write_heartbeat(settings, status=status, counts={'expired': 2},
                            error='RuntimeError' if status == 'error' else None)
    path = settings.data_dir / 'privacy_cleanup_heartbeat.json'
    data = json.loads(path.read_text())
    assert data['status'] == status and data['counts'] == {'expired': 2}
    assert data['pid'] == os.getpid() and isinstance(data['timestamp'], int)
    assert set(data) == {'pid', 'timestamp', 'status', 'counts'} | (
        {'error_type'} if status == 'error' else set())
    if status == 'error':
        assert data['error_type'] == 'RuntimeError'
    if os.name == 'posix':
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(settings.data_dir.iterdir()) == [path]


def test_two_writers_never_share_temporary_file(tmp_path, monkeypatch):
    settings = SimpleNamespace(data_dir=tmp_path)
    replace = worker.os.replace
    barrier = threading.Barrier(2)
    sources = []

    def synchronized_replace(source, target):
        sources.append(Path(source))
        barrier.wait(timeout=5)
        replace(source, target)

    monkeypatch.setattr(worker.os, 'replace', synchronized_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker._write_heartbeat, settings, status='ok',
                               counts={'writer': n}) for n in (1, 2)]
        for future in futures:
            future.result(timeout=10)
    assert len(set(sources)) == 2
    assert all(path.parent == tmp_path for path in sources)
    data = json.loads((tmp_path / 'privacy_cleanup_heartbeat.json').read_text())
    assert data['counts']['writer'] in (1, 2)
    assert list(tmp_path.iterdir()) == [tmp_path / 'privacy_cleanup_heartbeat.json']


def test_failed_replace_preserves_previous_file_and_removes_only_own_temp(tmp_path, monkeypatch):
    settings = SimpleNamespace(data_dir=tmp_path)
    path = tmp_path / 'privacy_cleanup_heartbeat.json'
    path.write_text('{"status":"previous"}')
    other = tmp_path / 'privacy_cleanup_heartbeat.other.tmp'
    other.write_text('another writer')

    def fail_replace(*_args):
        raise PermissionError('synthetic filesystem error')

    monkeypatch.setattr(worker.os, 'replace', fail_replace)
    with pytest.raises(PermissionError):
        worker._write_heartbeat(settings, status='ok')
    assert path.read_text() == '{"status":"previous"}'
    assert other.read_text() == 'another writer'
    assert set(tmp_path.iterdir()) == {path, other}


class Clock:
    def __init__(self, stop_at):
        self.elapsed = 0.0
        self.stop_at = stop_at

    def time(self):
        return 1_700_000_000 + self.elapsed

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.elapsed += seconds
        if self.elapsed >= self.stop_at:
            worker._stop()


def run_two_cycles(monkeypatch, tmp_path, *, acquired=True, cleanup_error=False):
    """Run the real loop and PostgreSQL-lock branch without a PostgreSQL server."""
    settings = SimpleNamespace(data_dir=tmp_path / 'cold' / 'data',
                               privacy_cleanup_interval_seconds=10)
    connections = []

    class Connection:
        closed = False
        unlocked = False

        def scalar(self, statement, params):
            assert 'pg_try_advisory_lock' in str(statement)
            assert params['key'] == worker._ADVISORY_LOCK_KEY
            return acquired

        def execute(self, statement, params):
            assert 'pg_advisory_unlock' in str(statement)
            self.unlocked = True

        def close(self):
            self.closed = True

    def connect():
        connection = Connection()
        connections.append(connection)
        return connection

    database = SimpleNamespace(backend='postgresql', engine=SimpleNamespace(connect=connect))
    disposed = []
    database.dispose = lambda: disposed.append(True)
    calls = []

    class Service:
        def run_retention_cleanup(self):
            calls.append(True)
            if cleanup_error:
                raise RuntimeError('synthetic cleanup failure')
            return {'pending_accounts': 0}

    clock = Clock(stop_at=20)
    monkeypatch.setattr(worker, '_STOP', False)
    monkeypatch.setattr(worker, 'load_settings', lambda: settings)
    monkeypatch.setattr(worker, 'configure_logging', lambda _settings: None)
    monkeypatch.setattr(worker, 'create_database', lambda _url: database)
    settings.database_url = 'synthetic-postgresql-no-connection'
    monkeypatch.setattr(worker, 'PrivacyRepository', lambda _db: object())
    monkeypatch.setattr(worker, 'PrivacyService', lambda _repo, _settings: Service())
    monkeypatch.setattr(worker.signal, 'signal', lambda *_args: None)
    monkeypatch.setattr(worker, 'time', clock)
    assert worker.main() == 0
    assert disposed == [True]
    assert len(connections) == 2
    assert all(conn.closed and conn.unlocked for conn in connections)
    assert len(calls) == (2 if acquired else 0)
    assert clock.elapsed == 20
    return settings


@pytest.mark.parametrize('acquired,cleanup_error,status', [
    (True, False, 'ok'), (False, False, 'lock_busy'), (True, True, 'error'),
])
def test_cold_postgresql_start_and_next_cycle(monkeypatch, tmp_path, caplog,
                                              acquired, cleanup_error, status):
    caplog.set_level(logging.INFO, logger='privacy_cleanup_worker')
    settings = run_two_cycles(monkeypatch, tmp_path, acquired=acquired,
                              cleanup_error=cleanup_error)
    data = json.loads((settings.data_dir / 'privacy_cleanup_heartbeat.json').read_text())
    assert data['status'] == status and data['timestamp'] == 1_700_000_010
    if cleanup_error:
        assert data['error_type'] == 'RuntimeError'
    else:
        assert 'Privacy retention cleanup failed' not in caplog.text


@pytest.mark.parametrize('acquired,cleanup_error', [(True, False), (False, False), (True, True)])
def test_heartbeat_io_failure_does_not_kill_loop_or_retry_cleanup_immediately(
        monkeypatch, tmp_path, caplog, acquired, cleanup_error):
    caplog.set_level(logging.INFO, logger='privacy_cleanup_worker')
    writes = []

    def broken_heartbeat(settings, **payload):
        writes.append(payload)
        raise PermissionError('synthetic-secret-path-must-not-be-logged')

    monkeypatch.setattr(worker, '_write_heartbeat', broken_heartbeat)
    run_two_cycles(monkeypatch, tmp_path, acquired=acquired, cleanup_error=cleanup_error)
    assert len(writes) == 2  # one publication attempt per scheduled iteration
    failures = [r for r in caplog.records
                if getattr(r, 'event', None) == 'privacy_retention_heartbeat_failed']
    assert len(failures) == 2
    assert all(r.error_type == 'PermissionError' and r.exc_info is None for r in failures)
    assert 'synthetic-secret-path-must-not-be-logged' not in caplog.text
    cleanup_failures = [r for r in caplog.records
                       if getattr(r, 'event', None) == 'privacy_retention_cleanup_failed']
    assert len(cleanup_failures) == (2 if cleanup_error else 0)


def test_transient_heartbeat_error_recovers_on_next_scheduled_cycle(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO, logger='privacy_cleanup_worker')
    original = worker._write_heartbeat
    calls = []

    def flaky(settings, **payload):
        calls.append(True)
        if len(calls) == 1:
            raise OSError('temporary storage failure')
        return original(settings, **payload)

    monkeypatch.setattr(worker, '_write_heartbeat', flaky)
    settings = run_two_cycles(monkeypatch, tmp_path)
    assert len(calls) == 2
    assert json.loads((settings.data_dir / 'privacy_cleanup_heartbeat.json').read_text())['status'] == 'ok'
    assert sum(getattr(r, 'event', None) == 'privacy_retention_heartbeat_failed'
               for r in caplog.records) == 1
