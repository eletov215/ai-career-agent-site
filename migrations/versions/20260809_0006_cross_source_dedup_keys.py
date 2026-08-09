"""Add non-destructive SEARCH-002 deduplication metadata.

Revision ID: 20260809_0006
Revises: 20260808_0005
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260809_0006"
down_revision: Union[str, None] = "20260808_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column("dedup_key", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("dedup_version", sa.Integer(), nullable=True))


def upgrade() -> None:
    _add_columns("vacancies")
    _add_columns("vacancy_source_records")
    op.create_index(
        "idx_vacancies_dedup_key",
        "vacancies",
        ["dedup_key"],
        unique=False,
    )
    op.create_index(
        "idx_vacancy_source_records_dedup_key",
        "vacancy_source_records",
        ["dedup_key"],
        unique=False,
    )
    # Existing source records stay NULL until their next provider refresh.
    # SEARCH-002 is deliberately non-destructive and does not guess historical
    # matches during deployment.


def _drop_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch:
        batch.drop_column("dedup_version")
        batch.drop_column("dedup_key")


def downgrade() -> None:
    op.drop_index(
        "idx_vacancy_source_records_dedup_key",
        table_name="vacancy_source_records",
    )
    op.drop_index("idx_vacancies_dedup_key", table_name="vacancies")
    _drop_columns("vacancy_source_records")
    _drop_columns("vacancies")
