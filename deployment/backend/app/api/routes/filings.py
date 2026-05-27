from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Filing, FilingStatus, FilingStatusHistory, ResidencyDetail, TaxpayerProfile
from app.schemas.filing import (
    FilingCreate,
    FilingListItem,
    FilingRead,
    FilingStatusUpdate,
    FilingUpdate,
    TaxpayerProfileRead,
    TaxpayerProfileUpsert,
)


router = APIRouter(prefix="/filings", tags=["filings"])


def _financial_year_for_assessment_year(assessment_year: int) -> tuple[int, int]:
    return assessment_year - 1, assessment_year


def _get_filing_or_404(db: Session, filing_id: str) -> Filing:
    filing = db.scalar(
        select(Filing)
        .where(Filing.id == filing_id)
        .options(joinedload(Filing.taxpayer_profile), joinedload(Filing.residency_detail))
    )
    if filing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filing not found")
    return filing


def _ensure_mutable(filing: Filing) -> None:
    if filing.read_only or filing.status == FilingStatus.submitted_done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted filing is read-only. Duplicate it to continue working.",
        )


def _add_status_history(
    db: Session,
    filing_id: str,
    from_status: FilingStatus | None,
    to_status: FilingStatus,
    reason: str | None = None,
) -> None:
    db.add(
        FilingStatusHistory(
            id=str(uuid4()),
            filing_id=filing_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )
    )


@router.post("", response_model=FilingRead, status_code=status.HTTP_201_CREATED)
def create_filing(payload: FilingCreate, db: Session = Depends(get_db)) -> Filing:
    fy_start, fy_end = _financial_year_for_assessment_year(payload.assessment_year)
    filing = Filing(
        id=str(uuid4()),
        assessment_year=payload.assessment_year,
        financial_year_start=fy_start,
        financial_year_end=fy_end,
        title=payload.title,
        status=FilingStatus.draft,
        read_only=False,
    )
    db.add(filing)
    _add_status_history(db, filing.id, None, FilingStatus.draft, "Initial filing created")
    db.commit()
    db.refresh(filing)
    return filing


@router.get("", response_model=list[FilingListItem])
def list_filings(db: Session = Depends(get_db)) -> list[Filing]:
    result = db.scalars(select(Filing).order_by(Filing.updated_at.desc(), Filing.created_at.desc()))
    return list(result.all())


@router.get("/{filing_id}", response_model=FilingRead)
def get_filing(filing_id: str, db: Session = Depends(get_db)) -> Filing:
    return _get_filing_or_404(db, filing_id)


@router.patch("/{filing_id}", response_model=FilingRead)
def update_filing(filing_id: str, payload: FilingUpdate, db: Session = Depends(get_db)) -> Filing:
    filing = _get_filing_or_404(db, filing_id)
    _ensure_mutable(filing)

    if payload.title is not None:
        filing.title = payload.title

    filing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(filing)
    return filing


@router.post("/{filing_id}/duplicate", response_model=FilingRead, status_code=status.HTTP_201_CREATED)
def duplicate_filing(filing_id: str, db: Session = Depends(get_db)) -> Filing:
    source = _get_filing_or_404(db, filing_id)
    duplicate = Filing(
        id=str(uuid4()),
        assessment_year=source.assessment_year,
        financial_year_start=source.financial_year_start,
        financial_year_end=source.financial_year_end,
        title=f"{source.title} (Copy)",
        status=FilingStatus.draft,
        read_only=False,
        source_filing_id=source.id,
    )
    db.add(duplicate)
    db.flush()

    if source.taxpayer_profile is not None:
        db.add(
            TaxpayerProfile(
                id=str(uuid4()),
                filing_id=duplicate.id,
                full_name=source.taxpayer_profile.full_name,
                pan=source.taxpayer_profile.pan,
                date_of_birth=source.taxpayer_profile.date_of_birth,
                residential_status=source.taxpayer_profile.residential_status,
                aadhaar_available=source.taxpayer_profile.aadhaar_available,
                email=source.taxpayer_profile.email,
                phone=source.taxpayer_profile.phone,
                employer_name=source.taxpayer_profile.employer_name,
                preferred_tax_regime=source.taxpayer_profile.preferred_tax_regime,
            )
        )

    if source.residency_detail is not None:
        db.add(
            ResidencyDetail(
                id=str(uuid4()),
                filing_id=duplicate.id,
                country_of_residence=source.residency_detail.country_of_residence,
                days_in_india=source.residency_detail.days_in_india,
                has_foreign_assets=source.residency_detail.has_foreign_assets,
                has_foreign_income=source.residency_detail.has_foreign_income,
            )
        )

    _add_status_history(db, duplicate.id, None, FilingStatus.draft, f"Duplicated from filing {source.id}")
    db.commit()
    db.refresh(duplicate)
    return duplicate


@router.post("/{filing_id}/mark-submitted", response_model=FilingRead)
def mark_filing_submitted(
    filing_id: str,
    payload: FilingStatusUpdate,
    db: Session = Depends(get_db),
) -> Filing:
    filing = _get_filing_or_404(db, filing_id)
    _ensure_mutable(filing)

    old_status = filing.status
    filing.status = FilingStatus.submitted_done
    filing.read_only = True
    filing.updated_at = datetime.utcnow()
    _add_status_history(db, filing.id, old_status, FilingStatus.submitted_done, payload.reason)
    db.commit()
    db.refresh(filing)
    return filing


@router.get("/{filing_id}/profile", response_model=TaxpayerProfileRead | None)
def get_taxpayer_profile(filing_id: str, db: Session = Depends(get_db)) -> TaxpayerProfile | None:
    filing = _get_filing_or_404(db, filing_id)
    return filing.taxpayer_profile


@router.put("/{filing_id}/profile", response_model=TaxpayerProfileRead)
def upsert_taxpayer_profile(
    filing_id: str,
    payload: TaxpayerProfileUpsert,
    db: Session = Depends(get_db),
) -> TaxpayerProfile:
    filing = _get_filing_or_404(db, filing_id)
    _ensure_mutable(filing)

    profile = filing.taxpayer_profile
    if profile is None:
        profile = TaxpayerProfile(id=str(uuid4()), filing_id=filing.id)
        db.add(profile)

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field_name, value)
    profile.updated_at = datetime.utcnow()
    filing.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)
    return profile
