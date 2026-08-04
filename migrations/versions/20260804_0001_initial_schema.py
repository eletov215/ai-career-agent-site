"""Create the initial cross-database schema.

Revision ID: 20260804_0001
Revises:
Create Date: 2026-08-04
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260804_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_datetime(value: object | None) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
    else:
        raw = str(value).strip()
        if not raw:
            return None
        if raw.isdigit():
            parsed = datetime.fromtimestamp(float(raw), tz=timezone.utc)
        else:
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return raw
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _search_blob(item: dict[str, object]) -> str:
    values = [
        item.get("title"),
        item.get("company"),
        item.get("location"),
        item.get("description"),
        item.get("requirements"),
        item.get("schedule"),
        item.get("employment"),
        item.get("experience"),
        item.get("currency"),
    ]
    return " ".join(str(value or "") for value in values).lower()


def _has_index(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(index.get("name") == name for index in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "accounts" not in tables:
        op.create_table(
            "accounts",
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("access_token", sa.Text(), nullable=False),
            sa.Column("refresh_token", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.BigInteger(), nullable=True),
            sa.Column("profile_json", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("user_id"),
        )

    if "hh_accounts" not in tables:
        op.create_table(
            "hh_accounts",
            sa.Column("user_id", sa.Text(), nullable=False),
            sa.Column("first_name", sa.Text(), nullable=True),
            sa.Column("last_name", sa.Text(), nullable=True),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("access_token", sa.Text(), nullable=False),
            sa.Column("refresh_token", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.BigInteger(), nullable=True),
            sa.Column("profile_json", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("user_id"),
        )

    if "vacancies" not in tables:
        op.create_table(
            "vacancies",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("external_id", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("company", sa.Text(), nullable=True),
            sa.Column("salary_from", sa.Float(), nullable=True),
            sa.Column("salary_to", sa.Float(), nullable=True),
            sa.Column("currency", sa.Text(), nullable=True),
            sa.Column("location", sa.Text(), nullable=True),
            sa.Column("remote", sa.Boolean(), nullable=False, server_default=sa.false()),
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
            sa.UniqueConstraint(
                "source",
                "external_id",
                name="uq_vacancies_source_external_id",
            ),
        )
    else:
        inspector = sa.inspect(bind)
        columns = {column["name"] for column in inspector.get_columns("vacancies")}
        if "experience" not in columns:
            op.add_column("vacancies", sa.Column("experience", sa.Text(), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "vacancies", "idx_vacancies_source_fetched"):
        op.create_index(
            "idx_vacancies_source_fetched",
            "vacancies",
            ["source", "fetched_at"],
            unique=False,
        )
    inspector = sa.inspect(bind)
    if not _has_index(inspector, "vacancies", "idx_vacancies_remote"):
        op.create_index(
            "idx_vacancies_remote",
            "vacancies",
            ["remote"],
            unique=False,
        )
    inspector = sa.inspect(bind)
    if not _has_index(inspector, "vacancies", "idx_vacancies_location"):
        op.create_index(
            "idx_vacancies_location",
            "vacancies",
            ["location"],
            unique=False,
        )

    rows = bind.execute(
        sa.text(
            "SELECT id, raw_json, search_text, experience, published_at FROM vacancies"
        )
    ).mappings()
    for row in rows:
        try:
            item = json.loads(row["raw_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            item = {}
        search_text = row["search_text"] or (_search_blob(item) if item else None)
        experience = row["experience"] or item.get("experience")
        published_at = _normalize_datetime(
            row["published_at"] or item.get("published_at")
        )
        bind.execute(
            sa.text(
                """
                UPDATE vacancies
                SET search_text = :search_text,
                    experience = :experience,
                    published_at = :published_at
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "search_text": search_text,
                "experience": experience,
                "published_at": published_at,
            },
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "vacancies" in tables:
        for index_name in (
            "idx_vacancies_location",
            "idx_vacancies_remote",
            "idx_vacancies_source_fetched",
        ):
            inspector = sa.inspect(op.get_bind())
            if _has_index(inspector, "vacancies", index_name):
                op.drop_index(index_name, table_name="vacancies")
        op.drop_table("vacancies")
    if "hh_accounts" in tables:
        op.drop_table("hh_accounts")
    if "accounts" in tables:
        op.drop_table("accounts")
