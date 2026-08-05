"""Legacy provider-specific OAuth tables retained for migration rollback.

DATA-002 copies these rows into ``oauth_connections``.  During the migration
verification window, OAuth repository writes are mirrored here as a controlled
rollback aid.  AUTH-002 can remove these tables after every connection belongs
to a first-party user and a verified backup/restore path exists.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SuperJobAccount(Base):
    __tablename__ = "accounts"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[int | None] = mapped_column(BigInteger)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class HeadHunterAccount(Base):
    __tablename__ = "hh_accounts"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[int | None] = mapped_column(BigInteger)
    profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
