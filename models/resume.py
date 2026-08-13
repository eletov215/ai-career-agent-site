"""PROF-003 resume drafts, immutable versions, assets, and PDF metadata."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ResumeDraft(Base):
    """Current mutable server-side resume-builder draft owned by one User."""

    __tablename__ = "resume_drafts"
    __table_args__ = (
        CheckConstraint("schema_version >= 1", name="ck_resume_drafts_schema_version"),
        CheckConstraint("revision >= 1", name="ck_resume_drafts_revision"),
        CheckConstraint(
            "completion_percent >= 0 AND completion_percent <= 100",
            name="ck_resume_drafts_completion_percent",
        ),
        Index("idx_resume_drafts_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    completion_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    user = relationship("User", back_populates="resume_drafts")
    versions = relationship(
        "ResumeVersion",
        back_populates="draft",
        passive_deletes=True,
        order_by="ResumeVersion.version",
    )
    assets = relationship(
        "ResumeAsset",
        back_populates="draft",
        passive_deletes=True,
    )
    exports = relationship(
        "ResumeExport",
        back_populates="draft",
        passive_deletes=True,
    )


class ResumeVersion(Base):
    """Immutable snapshot of a resume draft."""

    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint(
            "draft_id",
            "version",
            name="uq_resume_versions_draft_version",
        ),
        CheckConstraint("schema_version >= 1", name="ck_resume_versions_schema_version"),
        CheckConstraint("version >= 1", name="ck_resume_versions_version"),
        CheckConstraint("draft_revision >= 1", name="ck_resume_versions_draft_revision"),
        CheckConstraint(
            "reason IN ('checkpoint', 'export', 'restore')",
            name="ck_resume_versions_reason",
        ),
        Index("idx_resume_versions_draft_created", "draft_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resume_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    restored_from_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    draft = relationship("ResumeDraft", back_populates="versions")
    exports = relationship(
        "ResumeExport",
        back_populates="version_record",
        passive_deletes=True,
    )


class ResumeAsset(Base):
    """Durable owner-scoped image object stored outside the draft JSON."""

    __tablename__ = "resume_assets"
    __table_args__ = (
        UniqueConstraint(
            "draft_id",
            "kind",
            "sha256",
            name="uq_resume_assets_draft_kind_sha256",
        ),
        CheckConstraint(
            "kind IN ('photo', 'university_logo')",
            name="ck_resume_assets_kind",
        ),
        CheckConstraint(
            "byte_size > 0 AND byte_size <= 2097152",
            name="ck_resume_assets_byte_size",
        ),
        Index("idx_resume_assets_user_draft", "user_id", "draft_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resume_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    draft = relationship("ResumeDraft", back_populates="assets")


class ResumeExport(Base):
    """Metadata for a PDF generated from one saved resume version."""

    __tablename__ = "resume_exports"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_resume_exports_version"),
        CheckConstraint("page_count >= 1 AND page_count <= 100", name="ck_resume_exports_page_count"),
        CheckConstraint(
            "byte_size > 0 AND byte_size <= 52428800",
            name="ck_resume_exports_byte_size",
        ),
        Index("idx_resume_exports_draft_created", "draft_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resume_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    draft = relationship("ResumeDraft", back_populates="exports")
    version_record = relationship("ResumeVersion", back_populates="exports")
