"""Database runtime, migration helpers, and safe health metadata.

DATA-001 keeps application behavior compatible with the legacy SQLite file
while allowing the same code to run on PostgreSQL through ``DATABASE_URL``.
DATA-002 adds the repository-ready domain schema on top of that runtime.
No connection URL or password is exposed through logs or health responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from models import Base


INITIAL_REVISION = "20260804_0001"
CURRENT_REVISION = "20260812_0011"


class DatabaseConfigurationError(RuntimeError):
    """Raised when a database URL cannot be used safely."""


@dataclass(frozen=True, slots=True)
class DatabaseRuntime:
    """Engine and session factory shared by the application."""

    engine: Engine
    session_factory: sessionmaker[Session]
    url: URL
    backend: str
    persistent: bool

    def connect(self):  # noqa: ANN201 - mirrors SQLAlchemy Engine.connect
        return self.engine.connect()

    def session(self) -> Session:
        return self.session_factory()

    def dispose(self) -> None:
        self.engine.dispose()


def _ensure_sqlite_parent(url: URL) -> None:
    if url.get_backend_name() != "sqlite":
        return
    database = url.database
    if not database or database == ":memory:":
        return
    Path(database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


def create_database(database_url: str) -> DatabaseRuntime:
    """Create a SQLAlchemy runtime for SQLite or PostgreSQL/psycopg 3."""

    try:
        url = make_url(database_url)
    except Exception as exc:  # SQLAlchemy raises several URL parsing errors.
        raise DatabaseConfigurationError(
            "DATABASE_URL имеет неверный формат. Проверьте строку подключения."
        ) from exc

    backend = url.get_backend_name()
    driver = url.get_driver_name()
    if backend == "postgresql" and driver != "psycopg":
        raise DatabaseConfigurationError(
            "Для PostgreSQL требуется драйвер psycopg 3: postgresql+psycopg://."
        )
    if backend not in {"sqlite", "postgresql"}:
        raise DatabaseConfigurationError(
            "Поддерживаются только SQLite и PostgreSQL."
        )

    _ensure_sqlite_parent(url)

    common_options: dict[str, Any] = {
        "future": True,
        "pool_pre_ping": True,
        "hide_parameters": True,
    }
    if backend == "sqlite":
        common_options.update(
            {
                "poolclass": NullPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 10,
                },
            }
        )
    else:
        common_options.update(
            {
                "pool_size": 5,
                "max_overflow": 5,
                "pool_timeout": 30,
                "pool_recycle": 300,
                "connect_args": {"connect_timeout": 10},
            }
        )

    engine = create_engine(url, **common_options)
    if backend == "sqlite":
        _configure_sqlite(engine)

    sessions = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    persistent = backend == "postgresql"
    return DatabaseRuntime(
        engine=engine,
        session_factory=sessions,
        url=url,
        backend=backend,
        persistent=persistent,
    )


def alembic_config(database_url: str) -> AlembicConfig:
    """Build Alembic configuration without writing credentials to a file."""

    project_root = Path(__file__).resolve().parent
    config = AlembicConfig(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    # ConfigParser treats percent signs as interpolation markers.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_database(database_url: str, revision: str = "head") -> None:
    """Upgrade the configured database to a target Alembic revision."""

    try:
        _ensure_sqlite_parent(make_url(database_url))
    except Exception as exc:
        raise DatabaseConfigurationError(
            "DATABASE_URL имеет неверный формат. Проверьте строку подключения."
        ) from exc
    command.upgrade(alembic_config(database_url), revision)


def downgrade_database(database_url: str, revision: str) -> None:
    """Downgrade the configured database explicitly (maintenance use only)."""

    command.downgrade(alembic_config(database_url), revision)


def current_revision(engine: Engine) -> str | None:
    """Return the applied Alembic revision without exposing connection data."""

    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))


def database_health(runtime: DatabaseRuntime) -> dict[str, object]:
    """Return a secret-free database health summary."""

    try:
        with runtime.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        revision = current_revision(runtime.engine)
        return {
            "ok": True,
            "backend": runtime.backend,
            "persistent": runtime.persistent,
            "revision": revision,
        }
    except SQLAlchemyError:
        return {
            "ok": False,
            "backend": runtime.backend,
            "persistent": runtime.persistent,
            "revision": None,
        }


def create_schema_for_tests(runtime: DatabaseRuntime) -> None:
    """Create the current schema for isolated unit tests only.

    Production deployment uses Alembic. This helper preserves the small,
    standalone ``VacancyStore`` test API without coupling tests to subprocesses.
    """

    Base.metadata.create_all(runtime.engine)
