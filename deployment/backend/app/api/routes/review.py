from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CategoryAssignment, Filing, FilingStatus, GapItem
from app.schemas.review import (
    GapItemRead,
    GapResolvePayload,
    ReviewItemManualAdd,
    ReviewItemOverride,
    ReviewItemRead,
    ReviewItemSplit,
    ReviewItemStatusUpdate,
    ReviewItemView,
)
from app.services.review import (
    accept_review_item,
    add_manual_review_item,
    list_gap_items_for_filing,
    list_review_items_for_filing,
    mark_review_item_for_later,
    override_review_item,
    reject_review_item,
    resolve_gap_item,
    split_review_item,
)


router = APIRouter(tags=["review"])


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


def _get_review_item_or_404(db: Session, review_item_id: str) -> CategoryAssignment:
    assignment = db.get(CategoryAssignment, review_item_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")
    return assignment


@router.get("/filings/{filing_id}/review-items", response_model=list[ReviewItemView])
def list_review_items(filing_id: str, db: Session = Depends(get_db)) -> list[ReviewItemView]:
    _get_filing_or_404(db, filing_id)
    contexts = list_review_items_for_filing(db, filing_id)
    return [
        ReviewItemView(
            item=ReviewItemRead.model_validate(context.item),
            document_id=context.document_id,
            document_source=context.document_source,
            source_locator=context.source_locator,
            page_number=context.page_number,
            source_snippet=context.source_snippet,
        )
        for context in contexts
    ]


@router.post("/review-items/{review_item_id}/accept", response_model=ReviewItemRead)
def accept_item(review_item_id: str, db: Session = Depends(get_db)) -> ReviewItemRead:
    assignment = _get_review_item_or_404(db, review_item_id)
    filing = _get_filing_or_404(db, assignment.filing_id)
    _ensure_filing_mutable(filing)
    try:
        assignment = accept_review_item(db, review_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReviewItemRead.model_validate(assignment)


@router.post("/review-items/{review_item_id}/reject", response_model=ReviewItemRead)
def reject_item(
    review_item_id: str,
    payload: ReviewItemStatusUpdate,
    db: Session = Depends(get_db),
) -> ReviewItemRead:
    assignment = _get_review_item_or_404(db, review_item_id)
    filing = _get_filing_or_404(db, assignment.filing_id)
    _ensure_filing_mutable(filing)
    try:
        assignment = reject_review_item(db, review_item_id, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReviewItemRead.model_validate(assignment)


@router.post("/review-items/{review_item_id}/mark-for-later", response_model=ReviewItemRead)
def mark_for_later_item(
    review_item_id: str,
    payload: ReviewItemStatusUpdate,
    db: Session = Depends(get_db),
) -> ReviewItemRead:
    assignment = _get_review_item_or_404(db, review_item_id)
    filing = _get_filing_or_404(db, assignment.filing_id)
    _ensure_filing_mutable(filing)
    try:
        assignment = mark_review_item_for_later(db, review_item_id, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReviewItemRead.model_validate(assignment)


@router.post("/review-items/{review_item_id}/override", response_model=ReviewItemRead)
def override_item(
    review_item_id: str,
    payload: ReviewItemOverride,
    db: Session = Depends(get_db),
) -> ReviewItemRead:
    assignment = _get_review_item_or_404(db, review_item_id)
    filing = _get_filing_or_404(db, assignment.filing_id)
    _ensure_filing_mutable(filing)
    try:
        assignment = override_review_item(
            db=db,
            assignment_id=review_item_id,
            final_category=payload.final_category,
            description=payload.description,
            amount=payload.amount,
            amount_in_inr=payload.amount_in_inr,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReviewItemRead.model_validate(assignment)


@router.post("/review-items/{review_item_id}/split", response_model=list[ReviewItemRead])
def split_item(
    review_item_id: str,
    payload: ReviewItemSplit,
    db: Session = Depends(get_db),
) -> list[ReviewItemRead]:
    assignment = _get_review_item_or_404(db, review_item_id)
    filing = _get_filing_or_404(db, assignment.filing_id)
    _ensure_filing_mutable(filing)
    try:
        assignments = split_review_item(
            db=db,
            assignment_id=review_item_id,
            parts=[part.model_dump() for part in payload.parts],
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [ReviewItemRead.model_validate(assignment) for assignment in assignments]


@router.post("/filings/{filing_id}/review-items/manual", response_model=ReviewItemRead)
def add_manual_item(
    filing_id: str,
    payload: ReviewItemManualAdd,
    db: Session = Depends(get_db),
) -> ReviewItemRead:
    filing = _get_filing_or_404(db, filing_id)
    _ensure_filing_mutable(filing)
    assignment = add_manual_review_item(
        db=db,
        filing_id=filing_id,
        category=payload.category,
        description=payload.description,
        amount=payload.amount,
        currency_code=payload.currency_code,
        amount_in_inr=payload.amount_in_inr,
        reason=payload.reason,
    )
    return ReviewItemRead.model_validate(assignment)


@router.get("/filings/{filing_id}/gaps", response_model=list[GapItemRead])
def list_gaps(filing_id: str, db: Session = Depends(get_db)) -> list[GapItemRead]:
    _get_filing_or_404(db, filing_id)
    return [GapItemRead.model_validate(gap) for gap in list_gap_items_for_filing(db, filing_id)]


@router.post("/gaps/{gap_id}/resolve", response_model=GapItemRead)
def resolve_gap(gap_id: str, payload: GapResolvePayload, db: Session = Depends(get_db)) -> GapItemRead:
    gap = db.get(GapItem, gap_id)
    if gap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gap item not found")
    filing = _get_filing_or_404(db, gap.filing_id)
    _ensure_filing_mutable(filing)
    try:
        resolved = resolve_gap_item(
            db=db,
            gap_item_id=gap_id,
            resolution_action=payload.resolution_action,
            status=payload.status,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return GapItemRead.model_validate(resolved)
