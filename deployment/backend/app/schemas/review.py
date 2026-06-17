from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.processing import NormalizedTaxItemCategory
from app.models.review import GapResolutionStatus, GapSeverity, ReconciliationStatus, ReviewItemStatus


class ReviewItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filing_id: str
    normalized_tax_item_id: str | None
    source_parsed_field_id: str | None
    parent_assignment_id: str | None
    suggested_category: NormalizedTaxItemCategory
    final_category: NormalizedTaxItemCategory | None
    description: str
    amount: Decimal | None
    currency_code: str | None
    amount_in_inr: Decimal | None
    event_date: date | None
    confidence: Decimal
    status: ReviewItemStatus
    reconciliation_status: ReconciliationStatus
    reconciliation_context_json: dict | list | None
    created_at: datetime
    updated_at: datetime


class ReviewItemView(BaseModel):
    item: ReviewItemRead
    document_id: str | None
    document_source: str | None
    source_locator: str | None
    page_number: int | None
    source_snippet: str | None


class ReviewItemOverride(BaseModel):
    final_category: NormalizedTaxItemCategory
    description: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = None
    amount_in_inr: Decimal | None = None
    reason: str | None = Field(default=None, max_length=500)


class ReviewItemStatusUpdate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ReviewSplitPart(BaseModel):
    category: NormalizedTaxItemCategory
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal | None = None
    amount_in_inr: Decimal | None = None


class ReviewItemSplit(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
    parts: list[ReviewSplitPart] = Field(min_length=2)


class ReviewItemManualAdd(BaseModel):
    category: NormalizedTaxItemCategory
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal | None = None
    currency_code: str | None = Field(default=None, max_length=10)
    amount_in_inr: Decimal | None = None
    reason: str | None = Field(default=None, max_length=500)


class GapItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filing_id: str
    gap_key: str
    gap_code: str
    severity: GapSeverity
    user_message: str
    suggested_action: str
    resolution_status: GapResolutionStatus
    context_json: dict | list | None
    created_at: datetime
    updated_at: datetime


class GapResolvePayload(BaseModel):
    resolution_action: str = Field(min_length=1, max_length=50)
    status: GapResolutionStatus = GapResolutionStatus.resolved
    note: str | None = Field(default=None, max_length=500)
