from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import (
    Document,
    DocumentProcessingStatus,
    DocumentStorageRef,
    DocumentUploadEvent,
    DocumentVersion,
    Filing,
    FilingStatus,
)
from app.schemas.document import DocumentRead, DocumentUploadResponse
from app.services.storage import MIME_BY_EXTENSION, read_and_store_upload


router = APIRouter(tags=["documents"])


def _get_filing_or_404(db: Session, filing_id: str) -> Filing:
    filing = db.get(Filing, filing_id)
    if filing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filing not found")
    return filing


def _ensure_filing_mutable(filing: Filing) -> None:
    if filing.read_only or filing.status == FilingStatus.submitted_done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted filing is read-only. Duplicate it to continue working.",
        )


def _get_document_or_404(db: Session, document_id: str) -> Document:
    document = db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.versions).selectinload(DocumentVersion.storage_ref))
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _duplicate_warning(db: Session, filing_id: str, checksum_sha256: str) -> tuple[bool, list[str]]:
    duplicate = db.scalar(
        select(DocumentVersion)
        .join(Document, Document.id == DocumentVersion.document_id)
        .where(Document.filing_id == filing_id, DocumentVersion.checksum_sha256 == checksum_sha256)
    )
    if duplicate is None:
        return False, []
    return True, ["A document with the same checksum already exists for this filing."]


@router.post("/filings/{filing_id}/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    filing_id: str,
    file: UploadFile = File(...),
    source: str | None = Form(default=None),
    document_type: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    filing = _get_filing_or_404(db, filing_id)
    _ensure_filing_mutable(filing)

    document_id = str(uuid4())
    version_number = 1
    stored = await read_and_store_upload(file, filing_id, document_id, version_number)
    is_duplicate, warnings = _duplicate_warning(db, filing_id, stored.checksum_sha256)

    document = Document(
        id=document_id,
        filing_id=filing_id,
        source=source,
        document_type=document_type,
        processing_status=DocumentProcessingStatus.duplicate if is_duplicate else DocumentProcessingStatus.uploaded,
        is_duplicate=is_duplicate,
        updated_at=datetime.utcnow(),
    )
    db.add(document)
    db.flush()

    version = DocumentVersion(
        id=str(uuid4()),
        document_id=document.id,
        version_number=version_number,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type or MIME_BY_EXTENSION.get(stored.extension, "application/octet-stream"),
        file_extension=stored.extension,
        file_size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
    )
    db.add(version)
    db.flush()

    db.add(
        DocumentStorageRef(
            id=str(uuid4()),
            document_version_id=version.id,
            storage_path=stored.storage_path,
            stored_filename=stored.stored_filename,
        )
    )
    db.add(
        DocumentUploadEvent(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            event_type="upload",
            detail="Initial document upload",
        )
    )
    db.commit()

    response_document = _get_document_or_404(db, document.id)
    return DocumentUploadResponse(document=response_document, warnings=warnings)


@router.get("/filings/{filing_id}/documents", response_model=list[DocumentRead])
def list_documents_for_filing(filing_id: str, db: Session = Depends(get_db)) -> list[Document]:
    _get_filing_or_404(db, filing_id)
    result = db.scalars(
        select(Document)
        .where(Document.filing_id == filing_id)
        .options(selectinload(Document.versions).selectinload(DocumentVersion.storage_ref))
        .order_by(Document.created_at.desc())
    )
    return list(result.all())


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    return _get_document_or_404(db, document_id)


@router.post("/documents/{document_id}/replace", response_model=DocumentUploadResponse)
async def replace_document(
    document_id: str,
    file: UploadFile = File(...),
    source: str | None = Form(default=None),
    document_type: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    document = _get_document_or_404(db, document_id)
    filing = _get_filing_or_404(db, document.filing_id)
    _ensure_filing_mutable(filing)

    next_version_number = max((version.version_number for version in document.versions), default=0) + 1
    stored = await read_and_store_upload(file, filing.id, document.id, next_version_number)
    is_duplicate, warnings = _duplicate_warning(db, filing.id, stored.checksum_sha256)

    if source is not None:
        document.source = source
    if document_type is not None:
        document.document_type = document_type
    document.is_duplicate = is_duplicate
    document.processing_status = DocumentProcessingStatus.duplicate if is_duplicate else DocumentProcessingStatus.uploaded
    document.updated_at = datetime.utcnow()

    version = DocumentVersion(
        id=str(uuid4()),
        document_id=document.id,
        version_number=next_version_number,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type or MIME_BY_EXTENSION.get(stored.extension, "application/octet-stream"),
        file_extension=stored.extension,
        file_size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
    )
    db.add(version)
    db.flush()

    db.add(
        DocumentStorageRef(
            id=str(uuid4()),
            document_version_id=version.id,
            storage_path=stored.storage_path,
            stored_filename=stored.stored_filename,
        )
    )
    db.add(
        DocumentUploadEvent(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            event_type="replace",
            detail="Document version replaced",
        )
    )
    db.commit()

    response_document = _get_document_or_404(db, document.id)
    return DocumentUploadResponse(document=response_document, warnings=warnings)
