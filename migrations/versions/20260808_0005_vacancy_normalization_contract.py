"""Add canonical vacancy normalization codes for SEARCH-001.

Revision ID: 20260808_0005
Revises: 20260807_0004
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260808_0005"
down_revision: Union[str, None] = "20260807_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_contract_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column("work_format", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("employment_code", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("experience_code", sa.String(length=32), nullable=True))


def upgrade() -> None:
    _add_contract_columns("vacancies")
    _add_contract_columns("vacancy_source_records")

    op.create_index(
        "idx_vacancies_work_format",
        "vacancies",
        ["work_format"],
        unique=False,
    )
    op.create_index(
        "idx_vacancies_employment_code",
        "vacancies",
        ["employment_code"],
        unique=False,
    )
    op.create_index(
        "idx_vacancies_experience_code",
        "vacancies",
        ["experience_code"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_source_work_format",
        "vacancy_source_records",
        ["source", "work_format"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_source_employment_code",
        "vacancy_source_records",
        ["source", "employment_code"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_source_experience_code",
        "vacancy_source_records",
        ["source", "experience_code"],
        unique=False,
    )

    # The only legacy value that can be backfilled without inference is the
    # established boolean remote flag.  Other rows stay NULL and continue to
    # use the compatibility fallback until their next provider refresh.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE vacancy_source_records "
            "SET work_format = 'remote' "
            "WHERE remote = true AND work_format IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE vacancies "
            "SET work_format = 'remote' "
            "WHERE remote = true AND work_format IS NULL"
        )
    )


def _drop_contract_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.drop_column("experience_code")
        batch.drop_column("employment_code")
        batch.drop_column("work_format")


def downgrade() -> None:
    op.drop_index(
        "idx_vacancy_source_records_source_experience_code",
        table_name="vacancy_source_records",
    )
    op.drop_index(
        "idx_vacancy_source_records_source_employment_code",
        table_name="vacancy_source_records",
    )
    op.drop_index(
        "idx_vacancy_source_records_source_work_format",
        table_name="vacancy_source_records",
    )
    op.drop_index("idx_vacancies_experience_code", table_name="vacancies")
    op.drop_index("idx_vacancies_employment_code", table_name="vacancies")
    op.drop_index("idx_vacancies_work_format", table_name="vacancies")
    _drop_contract_columns("vacancy_source_records")
    _drop_contract_columns("vacancies")
