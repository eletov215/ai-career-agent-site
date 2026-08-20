

def test_observability_instrumentation_finds_provider_hook():
    from services.source_health_instrumentation import install_source_health_instrumentation

    assert install_source_health_instrumentation() is True


def test_provider_configuration_detection_does_not_expose_values(monkeypatch):
    from services.source_health import _configured

    monkeypatch.setenv("SUPERJOB_SECRET_KEY", "sensitive-value")
    configured, reason = _configured("superjob")
    assert configured is True
    assert reason == "configured"
    assert "sensitive" not in reason


def test_record_and_restart_style_read_persisted_state(monkeypatch):
    from contextlib import contextmanager
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from models.source_health import SourceHealthState
    import services.source_health as source_health

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SourceHealthState.__table__.create(engine)

    @contextmanager
    def local_scope():
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    monkeypatch.setattr(source_health, "_session_context", local_scope)
    monkeypatch.setenv("SOURCE_HEALTH_RECORDING_ENABLED", "1")
    monkeypatch.setenv("HH_SEARCH_ENABLED", "1")

    assert source_health.record_observation("hh", success=True, latency_ms=123)
    first = {item.provider: item for item in source_health.list_health_views()}
    assert first["hh"].last_latency_ms == 123
    assert first["hh"].availability == "available"
    assert first["hh"].consecutive_failures == 0

    assert source_health.record_observation("hh", success=False, error=TimeoutError("secret body"), latency_ms=456)
    second = {item.provider: item for item in source_health.list_health_views()}
    assert second["hh"].availability == "temporarily_unavailable"
    assert second["hh"].consecutive_failures == 1
    assert second["hh"].error_code == "TimeoutError"
