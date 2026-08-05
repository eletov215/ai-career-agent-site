"""Introduce the base domain model and repository-ready schema.

Revision ID: 20260804_0002
Revises: 20260804_0001
Create Date: 2026-08-04
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_0002"
down_revision: Union[str, None] = "20260804_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGACY_VACANCIES = "legacy_vacancies_data002"


def _table_names(bind) -> set[str]:  # noqa: ANN001
    return set(sa.inspect(bind).get_table_names())


def _deterministic_id(kind: str, *parts: object) -> str:
    value = ":".join(str(part) for part in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ai-career-agent:{kind}:{value}"))


def _reset_postgresql_sequence(bind, *, table: str, column: str) -> None:  # noqa: ANN001
    """Align a serial sequence after copying explicit legacy primary keys."""

    if bind.dialect.name != "postgresql":
        return
    allowed = {
        ("vacancy_source_records", "id"),
        ("vacancies", "id"),
    }
    if (table, column) not in allowed:
        raise ValueError("Unexpected sequence target")
    bind.execute(
        sa.text(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', '{column}'),
                COALESCE((SELECT MAX({column}) FROM {table}), 1),
                EXISTS(SELECT 1 FROM {table})
            )
            """
        )
    )


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("normalized_email", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("email_verified_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
    )
    op.create_index("idx_users_status", "users", ["status"], unique=False)


def _create_oauth_connections() -> None:
    op.create_table(
        "oauth_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_user_id", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.BigInteger(), nullable=True),
        sa.Column("profile_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "external_user_id",
            name="uq_oauth_connections_provider_external_user",
        ),
    )
    op.create_index(
        "idx_oauth_connections_user",
        "oauth_connections",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_oauth_connections_provider",
        "oauth_connections",
        ["provider"],
        unique=False,
    )


def _create_sync_runs() -> None:
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.BigInteger(), nullable=False),
        sa.Column("finished_at", sa.BigInteger(), nullable=True),
        sa.Column("target", sa.Integer(), nullable=True),
        sa.Column("processed", sa.Integer(), nullable=False),
        sa.Column("saved", sa.Integer(), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("error_type", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sync_runs_source_started",
        "sync_runs",
        ["source", "started_at"],
        unique=False,
    )
    op.create_index("idx_sync_runs_status", "sync_runs", ["status"], unique=False)


def _create_canonical_vacancies() -> None:
    op.create_table(
        "vacancies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("salary_from", sa.Float(), nullable=True),
        sa.Column("salary_to", sa.Float(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("remote", sa.Boolean(), nullable=False),
        sa.Column("schedule", sa.Text(), nullable=True),
        sa.Column("employment", sa.Text(), nullable=True),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("published_at", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_vacancies_fingerprint"),
    )
    op.create_index(
        "idx_vacancies_active_updated",
        "vacancies",
        ["is_active", "updated_at"],
        unique=False,
    )
    op.create_index("idx_vacancies_location", "vacancies", ["location"], unique=False)


def _create_vacancy_source_records() -> None:
    op.create_table(
        "vacancy_source_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("salary_from", sa.Float(), nullable=True),
        sa.Column("salary_to", sa.Float(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("remote", sa.Boolean(), nullable=False),
        sa.Column("schedule", sa.Text(), nullable=True),
        sa.Column("employment", sa.Text(), nullable=True),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("published_at", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("source_status", sa.String(length=32), nullable=False),
        sa.Column("first_seen_at", sa.BigInteger(), nullable=False),
        sa.Column("last_seen_at", sa.BigInteger(), nullable=False),
        sa.Column("fetched_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "external_id",
            name="uq_vacancy_source_records_source_external_id",
        ),
    )
    op.create_index(
        "idx_vacancy_source_records_vacancy",
        "vacancy_source_records",
        ["vacancy_id"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_source_fetched",
        "vacancy_source_records",
        ["source", "fetched_at"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_remote",
        "vacancy_source_records",
        ["remote"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_location",
        "vacancy_source_records",
        ["location"],
        unique=False,
    )


def _copy_legacy_oauth(bind) -> None:  # noqa: ANN001
    tables = _table_names(bind)
    existing = {
        (row[0], str(row[1]))
        for row in bind.execute(
            sa.text("SELECT provider, external_user_id FROM oauth_connections")
        ).all()
    }

    if "accounts" in tables:
        rows = bind.execute(sa.text("SELECT * FROM accounts")).mappings().all()
        for row in rows:
            key = ("superjob", str(row["user_id"]))
            if key in existing:
                continue
            bind.execute(
                sa.text(
                    """
                    INSERT INTO oauth_connections (
                        id, user_id, provider, external_user_id, display_name,
                        first_name, last_name, email, access_token, refresh_token,
                        expires_at, profile_json, created_at, updated_at
                    ) VALUES (
                        :id, NULL, :provider, :external_user_id, :display_name,
                        NULL, NULL, :email, :access_token, :refresh_token,
                        :expires_at, :profile_json, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": _deterministic_id("oauth", *key),
                    "provider": key[0],
                    "external_user_id": key[1],
                    "display_name": row["name"],
                    "email": row["email"],
                    "access_token": row["access_token"],
                    "refresh_token": row["refresh_token"],
                    "expires_at": row["expires_at"],
                    "profile_json": row["profile_json"],
                    "created_at": row["updated_at"],
                    "updated_at": row["updated_at"],
                },
            )
            existing.add(key)

    if "hh_accounts" in tables:
        rows = bind.execute(sa.text("SELECT * FROM hh_accounts")).mappings().all()
        for row in rows:
            key = ("headhunter", str(row["user_id"]))
            if key in existing:
                continue
            display_name = " ".join(
                part for part in (row["first_name"], row["last_name"]) if part
            ) or None
            bind.execute(
                sa.text(
                    """
                    INSERT INTO oauth_connections (
                        id, user_id, provider, external_user_id, display_name,
                        first_name, last_name, email, access_token, refresh_token,
                        expires_at, profile_json, created_at, updated_at
                    ) VALUES (
                        :id, NULL, :provider, :external_user_id, :display_name,
                        :first_name, :last_name, :email, :access_token, :refresh_token,
                        :expires_at, :profile_json, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": _deterministic_id("oauth", *key),
                    "provider": key[0],
                    "external_user_id": key[1],
                    "display_name": display_name,
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "email": row["email"],
                    "access_token": row["access_token"],
                    "refresh_token": row["refresh_token"],
                    "expires_at": row["expires_at"],
                    "profile_json": row["profile_json"],
                    "created_at": row["updated_at"],
                    "updated_at": row["updated_at"],
                },
            )
            existing.add(key)


def _copy_legacy_vacancies(bind) -> None:  # noqa: ANN001
    if LEGACY_VACANCIES not in _table_names(bind):
        return
    rows = bind.execute(
        sa.text(f"SELECT * FROM {LEGACY_VACANCIES}")
    ).mappings().all()
    for row in rows:
        canonical_id = _deterministic_id(
            "vacancy",
            row["source"],
            row["external_id"],
        )
        fingerprint = f"source:{row['source']}:{row['external_id']}"
        created_at = int(row["fetched_at"] or row["updated_at"] or 0)
        updated_at = int(row["updated_at"] or row["fetched_at"] or 0)
        bind.execute(
            sa.text(
                """
                INSERT INTO vacancies (
                    id, fingerprint, title, company, salary_from, salary_to,
                    currency, location, remote, schedule, employment, experience,
                    description, requirements, published_at, is_active,
                    created_at, updated_at
                ) VALUES (
                    :id, :fingerprint, :title, :company, :salary_from, :salary_to,
                    :currency, :location, :remote, :schedule, :employment, :experience,
                    :description, :requirements, :published_at, :is_active,
                    :created_at, :updated_at
                )
                """
            ),
            {
                "id": canonical_id,
                "fingerprint": fingerprint,
                "title": row["title"],
                "company": row["company"],
                "salary_from": row["salary_from"],
                "salary_to": row["salary_to"],
                "currency": row["currency"],
                "location": row["location"],
                "remote": row["remote"],
                "schedule": row["schedule"],
                "employment": row["employment"],
                "experience": row["experience"],
                "description": row["description"],
                "requirements": row["requirements"],
                "published_at": row["published_at"],
                "is_active": True,
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO vacancy_source_records (
                    id, vacancy_id, source, external_id, title, company,
                    salary_from, salary_to, currency, location, remote, schedule,
                    employment, experience, description, requirements, published_at,
                    url, search_text, raw_json, source_status, first_seen_at,
                    last_seen_at, fetched_at, updated_at
                ) VALUES (
                    :id, :vacancy_id, :source, :external_id, :title, :company,
                    :salary_from, :salary_to, :currency, :location, :remote, :schedule,
                    :employment, :experience, :description, :requirements, :published_at,
                    :url, :search_text, :raw_json, :source_status, :first_seen_at,
                    :last_seen_at, :fetched_at, :updated_at
                )
                """
            ),
            {
                **dict(row),
                "vacancy_id": canonical_id,
                "source_status": "active",
                "first_seen_at": created_at,
                "last_seen_at": updated_at,
            },
        )

    _reset_postgresql_sequence(
        bind, table="vacancy_source_records", column="id"
    )


def upgrade() -> None:
    bind = op.get_bind()
    tables = _table_names(bind)

    if "users" not in tables:
        _create_users()
    if "oauth_connections" not in tables:
        _create_oauth_connections()
    if "sync_runs" not in tables:
        _create_sync_runs()

    tables = _table_names(bind)
    if "vacancy_source_records" not in tables:
        if "vacancies" in tables:
            columns = {column["name"] for column in sa.inspect(bind).get_columns("vacancies")}
            if "source" in columns:
                op.rename_table("vacancies", LEGACY_VACANCIES)
                legacy_indexes = {
                    index.get("name")
                    for index in sa.inspect(bind).get_indexes(LEGACY_VACANCIES)
                    if index.get("name")
                }
                for index_name in (
                    "idx_vacancies_source_fetched",
                    "idx_vacancies_remote",
                    "idx_vacancies_location",
                ):
                    if index_name in legacy_indexes:
                        op.drop_index(index_name, table_name=LEGACY_VACANCIES)
        tables = _table_names(bind)
        if "vacancies" not in tables:
            _create_canonical_vacancies()
        _create_vacancy_source_records()
        _copy_legacy_vacancies(bind)
        if LEGACY_VACANCIES in _table_names(bind):
            op.drop_table(LEGACY_VACANCIES)

    _copy_legacy_oauth(bind)


def _create_legacy_vacancies_for_downgrade() -> None:
    op.create_table(
        LEGACY_VACANCIES,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("salary_from", sa.Float(), nullable=True),
        sa.Column("salary_to", sa.Float(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("remote", sa.Boolean(), nullable=False),
        sa.Column("schedule", sa.Text(), nullable=True),
        sa.Column("employment", sa.Text(), nullable=True),
        sa.Column("experience", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("published_at", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_vacancies_source_external_id"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _table_names(bind)

    if "vacancy_source_records" in tables:
        _create_legacy_vacancies_for_downgrade()
        bind.execute(
            sa.text(
                f"""
                INSERT INTO {LEGACY_VACANCIES} (
                    id, source, external_id, title, company, salary_from, salary_to,
                    currency, location, remote, schedule, employment, experience,
                    description, requirements, published_at, url, search_text,
                    raw_json, fetched_at, updated_at
                )
                SELECT
                    id, source, external_id, title, company, salary_from, salary_to,
                    currency, location, remote, schedule, employment, experience,
                    description, requirements, published_at, url, search_text,
                    raw_json, fetched_at, updated_at
                FROM vacancy_source_records
                """
            )
        )
        op.drop_table("vacancy_source_records")
        if "vacancies" in _table_names(bind):
            op.drop_table("vacancies")
        op.rename_table(LEGACY_VACANCIES, "vacancies")
        _reset_postgresql_sequence(bind, table="vacancies", column="id")
        op.create_index(
            "idx_vacancies_source_fetched",
            "vacancies",
            ["source", "fetched_at"],
            unique=False,
        )
        op.create_index("idx_vacancies_remote", "vacancies", ["remote"], unique=False)
        op.create_index("idx_vacancies_location", "vacancies", ["location"], unique=False)

    tables = _table_names(bind)
    if "sync_runs" in tables:
        op.drop_table("sync_runs")
    if "oauth_connections" in tables:
        op.drop_table("oauth_connections")
    if "users" in tables:
        op.drop_table("users")
