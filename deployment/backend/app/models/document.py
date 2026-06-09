from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentProcessingStatus(str, enum.Enum):
    uploaded = "uploaded"
    duplicate = "duplicate"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    needs_review = "needs_review"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus, name="document_processing_status", schema="app"),
        nullable=False,
        default=DocumentProcessingStatus.uploaded,
        index=True,
    )
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        order_by="DocumentVersion.version_number",
        cascade="all, delete-orphan",
    )
    upload_events: Mapped[list["DocumentUploadEvent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    validation_results: Mapped[list["DocumentValidationResult"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    raw_extractions: Mapped[list["RawExtraction"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    parsed_fields: Mapped[list["ParsedField"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    normalized_tax_items: Mapped[list["NormalizedTaxItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    foreign_income_events: Mapped[list["ForeignIncomeEvent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped[Document] = relationship(back_populates="versions")
    storage_ref: Mapped["DocumentStorageRef | None"] = relationship(
        back_populates="document_version",
        uselist=False,
        cascade="all, delete-orphan",
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="document_version")
    validation_results: Mapped[list["DocumentValidationResult"]] = relationship(back_populates="document_version")
    raw_extractions: Mapped[list["RawExtraction"]] = relationship(back_populates="document_version")
    parsed_fields: Mapped[list["ParsedField"]] = relationship(back_populates="document_version")
    normalized_tax_items: Mapped[list["NormalizedTaxItem"]] = relationship(back_populates="document_version")
    foreign_income_events: Mapped[list["ForeignIncomeEvent"]] = relationship(back_populates="document_version")


class DocumentStorageRef(Base):
    __tablename__ = "document_storage_refs"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app.document_versions.id", ondelete="CASCADE"), unique=True
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document_version: Mapped[DocumentVersion] = relationship(back_populates="storage_ref")


class DocumentUploadEvent(Base):
    __tablename__ = "document_upload_events"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("app.document_versions.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped[Document] = relationship(back_populates="upload_events")


from app.models.filing import Filing  # noqa: E402
from app.models.processing import (  # noqa: E402
    DocumentValidationResult,
    ForeignIncomeEvent,
    NormalizedTaxItem,
    ParsedField,
    ProcessingJob,
    RawExtraction,
)
