from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.processing import (
    DocumentCompletenessState,
    DocumentValidationState,
    NormalizedTaxItemCategory,
    ProcessingJobStatus,
    ProcessingJobType,
)


class ProcessingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    job_type: ProcessingJobType
    status: ProcessingJobStatus
    attempt_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class DocumentValidationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    processing_job_id: str | None
    validation_state: DocumentValidationState
    completeness_state: DocumentCompletenessState
    is_relevant: bool
    year_matches_filing: bool | None
    parseable: bool
    duplicate_detected: bool
    conflict_detected: bool
    detected_tax_year_label: str | None
    plain_language_reason: str
    created_at: datetime


class ParsedFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    raw_extraction_id: str | None
    field_name: str
    field_value_text: str
    value_type: str
    confidence: Decimal
    source_locator: str | None
    page_number: int | None
    currency_code: str | None
    event_date: date | None
    created_at: datetime


class NormalizedTaxItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    processing_job_id: str | None
    source_parsed_field_id: str | None
    category: NormalizedTaxItemCategory
    subcategory: str | None
    description: str
    amount: Decimal | None
    currency_code: str | None
    amount_in_inr: Decimal | None
    event_date: date | None
    confidence: Decimal
    review_status: str
    created_at: datetime


class ForeignIncomeEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_version_id: str
    normalized_tax_item_id: str | None
    event_type: str
    source_currency: str | None
    source_amount: Decimal | None
    withholding_amount: Decimal | None
    broker_platform: str | None
    country: str | None
    security_identifier: str | None
    event_date: date | None
    created_at: datetime


class DocumentProcessingRunResponse(BaseModel):
    document_id: str
    document_version_id: str
    jobs: list[ProcessingJobRead]
    validation_result: DocumentValidationResultRead | None
    parsed_fields_count: int
    normalized_tax_items_count: int
    foreign_income_events_count: int


class WorkerRunResponse(BaseModel):
    processed: bool
    job: ProcessingJobRead | None = None
    message: str
