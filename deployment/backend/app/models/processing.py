from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.review import CategoryAssignment


class ProcessingJobType(str, enum.Enum):
    validate_document = "validate_document"
    parse_document = "parse_document"
    run_ocr = "run_ocr"
    extract_fields = "extract_fields"
    normalize_tax_items = "normalize_tax_items"


class ProcessingJobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    needs_review = "needs_review"


class DocumentValidationState(str, enum.Enum):
    relevant = "relevant"
    possibly_relevant = "possibly_relevant"
    not_relevant = "not_relevant"
    unsupported = "unsupported"
    duplicate = "duplicate"
    corrupted_unreadable = "corrupted_unreadable"
    needs_user_review = "needs_user_review"


class DocumentCompletenessState(str, enum.Enum):
    complete = "complete"
    partial = "partial"
    incomplete = "incomplete"
    unknown = "unknown"


class NormalizedTaxItemCategory(str, enum.Enum):
    salary_income = "salary_income"
    interest_income = "interest_income"
    domestic_dividend_income = "domestic_dividend_income"
    foreign_dividend_income = "foreign_dividend_income"
    capital_gains = "capital_gains"
    deductions = "deductions"
    tds_credits = "tds_credits"
    advance_tax = "advance_tax"
    self_assessment_tax = "self_assessment_tax"
    other_sources = "other_sources"


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    job_type: Mapped[ProcessingJobType] = mapped_column(
        Enum(ProcessingJobType, name="processing_job_type", schema="app"),
        nullable=False,
    )
    status: Mapped[ProcessingJobStatus] = mapped_column(
        Enum(ProcessingJobStatus, name="processing_job_status", schema="app"),
        nullable=False,
        default=ProcessingJobStatus.pending,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="processing_jobs")
    document_version: Mapped["DocumentVersion"] = relationship(back_populates="processing_jobs")


class DocumentValidationResult(Base):
    __tablename__ = "document_validation_results"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    processing_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    validation_state: Mapped[DocumentValidationState] = mapped_column(
        Enum(DocumentValidationState, name="document_validation_state", schema="app"),
        nullable=False,
    )
    completeness_state: Mapped[DocumentCompletenessState] = mapped_column(
        Enum(DocumentCompletenessState, name="document_completeness_state", schema="app"),
        nullable=False,
        default=DocumentCompletenessState.unknown,
    )
    is_relevant: Mapped[bool] = mapped_column(nullable=False, default=False)
    year_matches_filing: Mapped[bool | None] = mapped_column(nullable=True)
    parseable: Mapped[bool] = mapped_column(nullable=False, default=False)
    duplicate_detected: Mapped[bool] = mapped_column(nullable=False, default=False)
    conflict_detected: Mapped[bool] = mapped_column(nullable=False, default=False)
    detected_tax_year_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plain_language_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="validation_results")
    document_version: Mapped["DocumentVersion"] = relationship(back_populates="validation_results")
    processing_job: Mapped[ProcessingJob | None] = relationship()


class RawExtraction(Base):
    __tablename__ = "raw_extractions"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    processing_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    extraction_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    content_format: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="raw_extractions")
    document_version: Mapped["DocumentVersion"] = relationship(back_populates="raw_extractions")
    processing_job: Mapped[ProcessingJob | None] = relationship()
    parsed_fields: Mapped[list["ParsedField"]] = relationship(back_populates="raw_extraction")


class ParsedField(Base):
    __tablename__ = "parsed_fields"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    raw_extraction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.raw_extractions.id", ondelete="SET NULL"),
        nullable=True,
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_value_text: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0.5000"))
    source_locator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="parsed_fields")
    document_version: Mapped["DocumentVersion"] = relationship(back_populates="parsed_fields")
    raw_extraction: Mapped[RawExtraction | None] = relationship(back_populates="parsed_fields")
    provenance_records: Mapped[list["FieldProvenance"]] = relationship(
        back_populates="parsed_field",
        cascade="all, delete-orphan",
    )


class FieldProvenance(Base):
    __tablename__ = "field_provenance"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parsed_field_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.parsed_fields.id", ondelete="CASCADE"),
        index=True,
    )
    raw_extraction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.raw_extractions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_locator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    parsed_field: Mapped[ParsedField] = relationship(back_populates="provenance_records")
    raw_extraction: Mapped[RawExtraction | None] = relationship()


class NormalizedTaxItem(Base):
    __tablename__ = "normalized_tax_items"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    processing_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.processing_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_parsed_field_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.parsed_fields.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[NormalizedTaxItemCategory] = mapped_column(
        Enum(NormalizedTaxItemCategory, name="normalized_tax_item_category", schema="app"),
        nullable=False,
    )
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    amount_in_inr: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0.5000"))
    review_status: Mapped[str] = mapped_column(String(50), nullable=False, default="candidate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="normalized_tax_items")
    document_version: Mapped["DocumentVersion"] = relationship(back_populates="normalized_tax_items")
    processing_job: Mapped[ProcessingJob | None] = relationship()
    source_parsed_field: Mapped[ParsedField | None] = relationship()
    foreign_income_events: Mapped[list["ForeignIncomeEvent"]] = relationship(
        back_populates="normalized_tax_item",
        cascade="all, delete-orphan",
    )
    category_assignments: Mapped[list["CategoryAssignment"]] = relationship(back_populates="normalized_tax_item")


class ForeignIncomeEvent(Base):
    __tablename__ = "foreign_income_events"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.documents.id", ondelete="CASCADE"), index=True)
    document_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    normalized_tax_item_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.normalized_tax_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    withholding_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    broker_platform: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    security_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="foreign_income_events")
    document_version: Mapped["DocumentVersion"] = relationship(back_populates="foreign_income_events")
    normalized_tax_item: Mapped[NormalizedTaxItem | None] = relationship(back_populates="foreign_income_events")

from app.models.document import Document, DocumentVersion  # noqa: E402
