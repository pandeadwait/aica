from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    Document,
    DocumentValidationResult,
    Filing,
    FilingStatus,
    ForeignIncomeEvent,
    NormalizedTaxItem,
    ParsedField,
    ProcessingJob,
)
from app.schemas.processing import (
    DocumentProcessingRunResponse,
    DocumentValidationResultRead,
    ForeignIncomeEventRead,
    NormalizedTaxItemRead,
    ParsedFieldRead,
    ProcessingJobRead,
    WorkerRunResponse,
)
from app.services.processing import (
    build_processing_summary,
    clear_phase3_outputs_for_version,
    enqueue_phase3_jobs,
    get_document_with_phase3_relations,
    latest_document_version,
    run_document_pipeline,
    run_next_pending_job,
)


router = APIRouter(tags=["processing"])
internal_router = APIRouter(prefix="/internal/processing", tags=["processing-internal"])


def _get_document_or_404(db: Session, document_id: str) -> Document:
    document = get_document_with_phase3_relations(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _ensure_filing_mutable(filing: Filing) -> None:
    if filing.read_only or filing.status == FilingStatus.submitted_done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted filing is read-only. Duplicate it to continue working.",
        )


@router.post("/documents/{document_id}/process", response_model=DocumentProcessingRunResponse, status_code=status.HTTP_202_ACCEPTED)
def process_document(
    document_id: str,
    run_now: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> DocumentProcessingRunResponse:
    document = _get_document_or_404(db, document_id)
    filing = db.get(Filing, document.filing_id)
    if filing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filing not found")
    _ensure_filing_mutable(filing)

    version = latest_document_version(document)
    clear_phase3_outputs_for_version(db, version.id)
    enqueue_phase3_jobs(db, document)
    db.commit()

    if run_now:
        run_document_pipeline(db, document.id)

    refreshed = _get_document_or_404(db, document_id)
    return DocumentProcessingRunResponse(**build_processing_summary(db, refreshed))


@router.get("/documents/{document_id}/processing-jobs", response_model=list[ProcessingJobRead])
def list_processing_jobs(document_id: str, db: Session = Depends(get_db)) -> list[ProcessingJob]:
    _get_document_or_404(db, document_id)
    result = db.scalars(
        select(ProcessingJob).where(ProcessingJob.document_id == document_id).order_by(ProcessingJob.created_at.asc())
    )
    return list(result.all())


@router.get("/documents/{document_id}/validation-results", response_model=list[DocumentValidationResultRead])
def list_validation_results(document_id: str, db: Session = Depends(get_db)) -> list[DocumentValidationResult]:
    _get_document_or_404(db, document_id)
    result = db.scalars(
        select(DocumentValidationResult)
        .where(DocumentValidationResult.document_id == document_id)
        .order_by(DocumentValidationResult.created_at.desc())
    )
    return list(result.all())


@router.get("/documents/{document_id}/parsed-fields", response_model=list[ParsedFieldRead])
def list_parsed_fields(document_id: str, db: Session = Depends(get_db)) -> list[ParsedField]:
    _get_document_or_404(db, document_id)
    result = db.scalars(
        select(ParsedField).where(ParsedField.document_id == document_id).order_by(ParsedField.created_at.asc())
    )
    return list(result.all())


@router.get("/documents/{document_id}/normalized-tax-items", response_model=list[NormalizedTaxItemRead])
def list_normalized_tax_items(document_id: str, db: Session = Depends(get_db)) -> list[NormalizedTaxItem]:
    _get_document_or_404(db, document_id)
    result = db.scalars(
        select(NormalizedTaxItem)
        .where(NormalizedTaxItem.document_id == document_id)
        .order_by(NormalizedTaxItem.created_at.asc())
    )
    return list(result.all())


@router.get("/documents/{document_id}/foreign-income-events", response_model=list[ForeignIncomeEventRead])
def list_foreign_income_events(document_id: str, db: Session = Depends(get_db)) -> list[ForeignIncomeEvent]:
    _get_document_or_404(db, document_id)
    result = db.scalars(
        select(ForeignIncomeEvent)
        .where(ForeignIncomeEvent.document_id == document_id)
        .order_by(ForeignIncomeEvent.created_at.asc())
    )
    return list(result.all())


@internal_router.post("/run-next", response_model=WorkerRunResponse)
def run_next_processing_job(db: Session = Depends(get_db)) -> WorkerRunResponse:
    job = run_next_pending_job(db)
    if job is None:
        return WorkerRunResponse(processed=False, job=None, message="No pending processing jobs.")
    return WorkerRunResponse(processed=True, job=job, message="Processed the next pending processing job.")
