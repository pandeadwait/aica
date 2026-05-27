from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.filing import FilingStatus


class FilingCreate(BaseModel):
    assessment_year: int = Field(ge=2000, le=2100)
    title: str = Field(min_length=3, max_length=255)


class FilingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)


class FilingStatusUpdate(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class TaxpayerProfileUpsert(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    pan: str | None = Field(default=None, min_length=10, max_length=10)
    date_of_birth: date | None = None
    residential_status: str | None = Field(default=None, max_length=50)
    aadhaar_available: bool | None = None
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    employer_name: str | None = Field(default=None, max_length=255)
    preferred_tax_regime: str | None = Field(default=None, max_length=30)

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.upper()
        if len(normalized) != 10 or not normalized[:5].isalpha() or not normalized[5:9].isdigit() or not normalized[9].isalpha():
            raise ValueError("PAN must be in valid 10-character format")
        return normalized


class TaxpayerProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str | None
    pan: str | None
    date_of_birth: date | None
    residential_status: str | None
    aadhaar_available: bool | None
    email: str | None
    phone: str | None
    employer_name: str | None
    preferred_tax_regime: str | None
    created_at: datetime
    updated_at: datetime


class FilingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_year: int
    financial_year_start: int
    financial_year_end: int
    title: str
    status: FilingStatus
    read_only: bool
    source_filing_id: str | None
    created_at: datetime
    updated_at: datetime
    taxpayer_profile: TaxpayerProfileRead | None = None


class FilingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_year: int
    financial_year_start: int
    financial_year_end: int
    title: str
    status: FilingStatus
    read_only: bool
    created_at: datetime
    updated_at: datetime

