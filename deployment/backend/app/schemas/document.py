from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentProcessingStatus


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_number: int
    original_filename: str
    mime_type: str
    file_extension: str
    file_size_bytes: int
    checksum_sha256: str
    uploaded_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filing_id: str
    document_type: str | None
    source: str | None
    processing_status: DocumentProcessingStatus
    is_duplicate: bool
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionRead] = []


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filing_id: str
    document_type: str | None
    source: str | None
    processing_status: DocumentProcessingStatus
    is_duplicate: bool
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    warnings: list[str] = []


class DocumentUploadMetadata(BaseModel):
    source: str | None = Field(default=None, max_length=100)
    document_type: str | None = Field(default=None, max_length=100)

