"""Structured owner-scoped career profile persistence for PROF-001."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CareerProfile(Base):
    """One current structured career profile per first-party user."""

    __tablename__ = "career_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_career_profiles_user_id"),
        CheckConstraint("schema_version >= 1", name="ck_career_profiles_schema_version"),
        CheckConstraint("version >= 1", name="ck_career_profiles_version"),
        CheckConstraint(
            "completion_percent >= 0 AND completion_percent <= 100",
            name="ck_career_profiles_completion_percent",
        ),
        Index("idx_career_profiles_updated", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    headline: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    contacts_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    goals_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    geography_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    salary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    skills_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    employment_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    achievements_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    education_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    languages_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    completion_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confirmed_at: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    user = relationship("User", back_populates="career_profile")
    versions = relationship(
        "CareerProfileVersion",
        back_populates="profile",
        passive_deletes=True,
        order_by="CareerProfileVersion.version.desc()",
    )


class CareerProfileVersion(Base):
    """Immutable full snapshot for every material profile change."""

    __tablename__ = "career_profile_versions"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "version",
            name="uq_career_profile_versions_profile_version",
        ),
        CheckConstraint(
            "schema_version >= 1",
            name="ck_career_profile_versions_schema_version",
        ),
        CheckConstraint("version >= 1", name="ck_career_profile_versions_version"),
        CheckConstraint(
            "source_kind IN ('manual', 'resume_import')",
            name="ck_career_profile_versions_source_kind",
        ),
        Index(
            "idx_career_profile_versions_profile_created",
            "profile_id",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("career_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_sections_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    provenance_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    profile = relationship("CareerProfile", back_populates="versions")
