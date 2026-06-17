from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CategoryAssignment,
    Document,
    DocumentProcessingStatus,
    DocumentValidationResult,
    Filing,
    ForeignIncomeEvent,
    GapItem,
    GapResolution,
    GapResolutionStatus,
    GapSeverity,
    ManualOverride,
    NormalizedTaxItem,
    NormalizedTaxItemCategory,
    ParsedField,
    ReconciliationStatus,
    ReviewItemStatus,
    ReviewSession,
)

FORM16_TYPES = {"form16"}
FORM26AS_TYPES = {"form26as"}
AIS_TYPES = {"ais", "tis"}
INTEREST_SUPPORT_TYPES = {"interest_certificate", "bank_statement", "ais", "form26as"}
DEDUCTION_SUPPORT_TYPES = {
    "insurance_premium_proof",
    "ppf_elss_proof",
    "donation_receipt",
    "tuition_fee_receipt",
    "medical_insurance_document",
    "rent_receipt",
    "home_loan_certificate",
}
DIVIDEND_SUPPORT_TYPES = {"ais", "broker_statement", "dividend_statement", "foreign_dividend_statement"}
CAPITAL_GAINS_SUPPORT_TYPES = {"ais", "broker_statement", "capital_gains_statement", "rsu_statement", "esop_statement"}
AUTHORITATIVE_TDS_TYPES = FORM16_TYPES | FORM26AS_TYPES | AIS_TYPES
AUTHORITATIVE_SALARY_TYPES = FORM16_TYPES | AIS_TYPES
AUTHORITATIVE_INTEREST_TYPES = INTEREST_SUPPORT_TYPES
AMOUNT_TOLERANCE = Decimal("1.00")


@dataclass
class ReviewItemContext:
    item: CategoryAssignment
    document_id: str | None
    document_source: str | None
    source_locator: str | None
    page_number: int | None
    source_snippet: str | None


def ensure_review_state_for_filing(db: Session, filing_id: str) -> None:
    _ensure_review_session(db, filing_id)
    normalized_items = list(
        db.scalars(
            select(NormalizedTaxItem)
            .join(Document, Document.id == NormalizedTaxItem.document_id)
            .where(Document.filing_id == filing_id)
            .options(selectinload(NormalizedTaxItem.source_parsed_field))
        ).all()
    )
    existing_by_normalized_id = {
        assignment.normalized_tax_item_id
        for assignment in db.scalars(
            select(CategoryAssignment)
            .where(CategoryAssignment.filing_id == filing_id, CategoryAssignment.parent_assignment_id.is_(None))
        ).all()
        if assignment.normalized_tax_item_id is not None
    }
    for item in normalized_items:
        if item.id in existing_by_normalized_id:
            continue
        db.add(
            CategoryAssignment(
                id=str(uuid4()),
                filing_id=filing_id,
                normalized_tax_item_id=item.id,
                source_parsed_field_id=item.source_parsed_field_id,
                suggested_category=item.category,
                final_category=None,
                description=item.description,
                amount=item.amount,
                currency_code=item.currency_code,
                amount_in_inr=item.amount_in_inr,
                event_date=item.event_date,
                confidence=item.confidence,
                status=ReviewItemStatus.candidate,
                reconciliation_status=ReconciliationStatus.unverified,
                updated_at=datetime.utcnow(),
            )
        )
    db.flush()
    _refresh_reconciliation_state(db, filing_id)
    db.flush()


def list_review_items_for_filing(db: Session, filing_id: str) -> list[ReviewItemContext]:
    ensure_review_state_for_filing(db, filing_id)
    _touch_review_session(db, filing_id)
    assignments = list(
        db.scalars(
            select(CategoryAssignment)
            .where(CategoryAssignment.filing_id == filing_id)
            .options(
                selectinload(CategoryAssignment.normalized_tax_item).selectinload(NormalizedTaxItem.document),
                selectinload(CategoryAssignment.source_parsed_field).selectinload(ParsedField.provenance_records),
            )
            .order_by(CategoryAssignment.created_at.asc())
        ).all()
    )
    contexts: list[ReviewItemContext] = []
    for assignment in assignments:
        normalized = assignment.normalized_tax_item
        document = normalized.document if normalized is not None else None
        parsed_field = assignment.source_parsed_field
        snippet = None
        if parsed_field is not None and parsed_field.provenance_records:
            snippet = parsed_field.provenance_records[0].source_snippet
        contexts.append(
            ReviewItemContext(
                item=assignment,
                document_id=document.id if document is not None else None,
                document_source=document.source if document is not None else None,
                source_locator=parsed_field.source_locator if parsed_field is not None else None,
                page_number=parsed_field.page_number if parsed_field is not None else None,
                source_snippet=snippet,
            )
        )
    db.commit()
    return contexts


def accept_review_item(db: Session, assignment_id: str) -> CategoryAssignment:
    assignment = _get_assignment_or_raise(db, assignment_id)
    if assignment.final_category is None:
        assignment.final_category = assignment.suggested_category
    assignment.status = ReviewItemStatus.accepted
    assignment.updated_at = datetime.utcnow()
    _record_override(db, assignment, "accept", assignment.final_category, assignment.final_category, None, None)
    db.commit()
    refresh_gap_items(db, assignment.filing_id)
    db.commit()
    db.refresh(assignment)
    return assignment


def override_review_item(
    db: Session,
    assignment_id: str,
    final_category: NormalizedTaxItemCategory,
    description: str | None,
    amount: Decimal | None,
    amount_in_inr: Decimal | None,
    reason: str | None,
) -> CategoryAssignment:
    assignment = _get_assignment_or_raise(db, assignment_id)
    old_category = assignment.final_category or assignment.suggested_category
    assignment.final_category = final_category
    if description is not None:
        assignment.description = description
    if amount is not None:
        assignment.amount = amount
    if amount_in_inr is not None:
        assignment.amount_in_inr = amount_in_inr
    assignment.status = ReviewItemStatus.overridden
    assignment.updated_at = datetime.utcnow()
    _record_override(
        db,
        assignment,
        "override",
        old_category,
        final_category,
        reason,
        {
            "description": assignment.description,
            "amount": str(assignment.amount) if assignment.amount is not None else None,
            "amount_in_inr": str(assignment.amount_in_inr) if assignment.amount_in_inr is not None else None,
        },
    )
    db.commit()
    refresh_gap_items(db, assignment.filing_id)
    db.commit()
    db.refresh(assignment)
    return assignment


def reject_review_item(db: Session, assignment_id: str, reason: str | None) -> CategoryAssignment:
    assignment = _get_assignment_or_raise(db, assignment_id)
    old_category = assignment.final_category or assignment.suggested_category
    assignment.status = ReviewItemStatus.rejected
    assignment.updated_at = datetime.utcnow()
    _record_override(db, assignment, "reject", old_category, None, reason, None)
    db.commit()
    refresh_gap_items(db, assignment.filing_id)
    db.commit()
    db.refresh(assignment)
    return assignment


def mark_review_item_for_later(db: Session, assignment_id: str, reason: str | None) -> CategoryAssignment:
    assignment = _get_assignment_or_raise(db, assignment_id)
    old_category = assignment.final_category or assignment.suggested_category
    assignment.status = ReviewItemStatus.marked_for_later
    assignment.updated_at = datetime.utcnow()
    _record_override(db, assignment, "mark_for_later", old_category, old_category, reason, None)
    db.commit()
    refresh_gap_items(db, assignment.filing_id)
    db.commit()
    db.refresh(assignment)
    return assignment


def add_manual_review_item(
    db: Session,
    filing_id: str,
    category: NormalizedTaxItemCategory,
    description: str,
    amount: Decimal | None,
    currency_code: str | None,
    amount_in_inr: Decimal | None,
    reason: str | None,
) -> CategoryAssignment:
    assignment = CategoryAssignment(
        id=str(uuid4()),
        filing_id=filing_id,
        normalized_tax_item_id=None,
        source_parsed_field_id=None,
        parent_assignment_id=None,
        suggested_category=category,
        final_category=category,
        description=description,
        amount=amount,
        currency_code=currency_code,
        amount_in_inr=amount_in_inr,
        event_date=None,
        confidence=Decimal("1.0000"),
        status=ReviewItemStatus.overridden,
        reconciliation_status=ReconciliationStatus.unverified,
        reconciliation_context_json={"manual_entry": True},
        updated_at=datetime.utcnow(),
    )
    db.add(assignment)
    db.flush()
    _record_override(
        db,
        assignment,
        "manual_add",
        None,
        category,
        reason,
        {
            "description": description,
            "amount": str(amount) if amount is not None else None,
            "amount_in_inr": str(amount_in_inr) if amount_in_inr is not None else None,
            "currency_code": currency_code,
        },
    )
    db.commit()
    refresh_gap_items(db, filing_id)
    db.commit()
    db.refresh(assignment)
    return assignment


def split_review_item(
    db: Session,
    assignment_id: str,
    parts: list[dict[str, object]],
    reason: str | None,
) -> list[CategoryAssignment]:
    assignment = _get_assignment_or_raise(db, assignment_id)
    assignment.status = ReviewItemStatus.split
    assignment.updated_at = datetime.utcnow()
    old_category = assignment.final_category or assignment.suggested_category
    created_parts: list[CategoryAssignment] = []
    for part in parts:
        child = CategoryAssignment(
            id=str(uuid4()),
            filing_id=assignment.filing_id,
            normalized_tax_item_id=assignment.normalized_tax_item_id,
            source_parsed_field_id=assignment.source_parsed_field_id,
            parent_assignment_id=assignment.id,
            suggested_category=part["category"],
            final_category=part["category"],
            description=part["description"],
            amount=part.get("amount"),
            currency_code=assignment.currency_code,
            amount_in_inr=part.get("amount_in_inr"),
            event_date=assignment.event_date,
            confidence=assignment.confidence,
            status=ReviewItemStatus.overridden,
            updated_at=datetime.utcnow(),
        )
        db.add(child)
        db.flush()
        _record_override(
            db,
            child,
            "split_part",
            old_category,
            child.final_category,
            reason,
            {
                "parent_assignment_id": assignment.id,
            },
        )
        created_parts.append(child)
    _record_override(
        db,
        assignment,
        "split",
        old_category,
        None,
        reason,
        {"parts_count": len(created_parts)},
    )
    db.commit()
    refresh_gap_items(db, assignment.filing_id)
    db.commit()
    for child in created_parts:
        db.refresh(child)
    return created_parts


def refresh_gap_items(db: Session, filing_id: str) -> list[GapItem]:
    ensure_review_state_for_filing(db, filing_id)
    existing = {
        gap.gap_key: gap
        for gap in db.scalars(select(GapItem).where(GapItem.filing_id == filing_id)).all()
    }
    desired = {gap["gap_key"]: gap for gap in _compute_gap_definitions(db, filing_id)}

    for gap_key, gap_def in desired.items():
        gap_item = existing.get(gap_key)
        if gap_item is None:
            gap_item = GapItem(
                id=str(uuid4()),
                filing_id=filing_id,
                gap_key=gap_key,
                gap_code=gap_def["gap_code"],
                severity=gap_def["severity"],
                user_message=gap_def["user_message"],
                suggested_action=gap_def["suggested_action"],
                resolution_status=GapResolutionStatus.open,
                context_json=gap_def.get("context_json"),
                updated_at=datetime.utcnow(),
            )
            db.add(gap_item)
        else:
            gap_item.gap_code = gap_def["gap_code"]
            gap_item.severity = gap_def["severity"]
            gap_item.user_message = gap_def["user_message"]
            gap_item.suggested_action = gap_def["suggested_action"]
            gap_item.context_json = gap_def.get("context_json")
            gap_item.updated_at = datetime.utcnow()

    obsolete_keys = set(existing) - set(desired)
    if obsolete_keys:
        obsolete_ids = [existing[key].id for key in obsolete_keys]
        db.execute(
            delete(GapResolution).where(
                GapResolution.gap_item_id.in_(obsolete_ids)
            )
        )
        db.execute(delete(GapItem).where(GapItem.id.in_(obsolete_ids)))

    db.flush()
    return list(
        db.scalars(
            select(GapItem).where(GapItem.filing_id == filing_id).order_by(GapItem.created_at.asc())
        ).all()
    )


def list_gap_items_for_filing(db: Session, filing_id: str) -> list[GapItem]:
    refresh_gap_items(db, filing_id)
    db.commit()
    return list(
        db.scalars(
            select(GapItem).where(GapItem.filing_id == filing_id).order_by(GapItem.created_at.asc())
        ).all()
    )


def resolve_gap_item(
    db: Session,
    gap_item_id: str,
    resolution_action: str,
    status: GapResolutionStatus,
    note: str | None,
) -> GapItem:
    gap_item = db.get(GapItem, gap_item_id)
    if gap_item is None:
        raise ValueError("Gap item not found")
    gap_item.resolution_status = status
    gap_item.updated_at = datetime.utcnow()
    db.add(
        GapResolution(
            id=str(uuid4()),
            gap_item_id=gap_item.id,
            resolution_action=resolution_action,
            note=note,
        )
    )
    db.commit()
    db.refresh(gap_item)
    return gap_item


def _compute_gap_definitions(db: Session, filing_id: str) -> list[dict[str, object]]:
    gaps: list[dict[str, object]] = []
    filing = db.scalar(
        select(Filing)
        .where(Filing.id == filing_id)
        .options(selectinload(Filing.taxpayer_profile))
    )
    if filing is None:
        return gaps

    if filing.taxpayer_profile is None or not filing.taxpayer_profile.pan:
        gaps.append(
            {
                "gap_key": "profile:missing_basic_profile",
                "gap_code": "missing_basic_profile",
                "severity": GapSeverity.critical,
                "user_message": "Basic taxpayer profile information is incomplete.",
                "suggested_action": "Add the taxpayer profile details before calculation.",
                "context_json": {"missing_pan": filing.taxpayer_profile.pan if filing.taxpayer_profile else None},
            }
        )

    documents = list(db.scalars(select(Document).where(Document.filing_id == filing_id)).all())
    present_document_types = _present_document_types(documents)
    if not documents:
        gaps.append(
            {
                "gap_key": "documents:none_uploaded",
                "gap_code": "no_documents_uploaded",
                "severity": GapSeverity.critical,
                "user_message": "No tax documents have been uploaded for this filing.",
                "suggested_action": "Upload the relevant tax documents to continue review.",
                "context_json": None,
            }
        )
        return gaps

    not_ready_documents = [
        document.id
        for document in documents
        if document.processing_status in {
            DocumentProcessingStatus.uploaded,
            DocumentProcessingStatus.queued,
            DocumentProcessingStatus.processing,
            DocumentProcessingStatus.failed,
            DocumentProcessingStatus.needs_review,
        }
    ]
    if not_ready_documents:
        gaps.append(
            {
                "gap_key": "documents:not_ready",
                "gap_code": "documents_not_ready",
                "severity": GapSeverity.warning,
                "user_message": "Some uploaded documents still need processing or review.",
                "suggested_action": "Finish document processing and resolve any review issues.",
                "context_json": {"document_ids": not_ready_documents},
            }
        )

    validation_results = list(
        db.scalars(
            select(DocumentValidationResult)
            .join(Document, Document.id == DocumentValidationResult.document_id)
            .where(Document.filing_id == filing_id)
            .order_by(DocumentValidationResult.created_at.desc())
        ).all()
    )
    for result in validation_results:
        if result.year_matches_filing is False:
            gaps.append(
                {
                    "gap_key": f"validation:year_mismatch:{result.document_id}",
                    "gap_code": "year_mismatch",
                    "severity": GapSeverity.warning,
                    "user_message": "A document may belong to a different financial or assessment year.",
                    "suggested_action": "Review the year context for the flagged document.",
                    "context_json": {
                        "document_id": result.document_id,
                        "detected_tax_year_label": result.detected_tax_year_label,
                    },
                }
            )

    review_items = list(
        db.scalars(
            select(CategoryAssignment)
            .where(CategoryAssignment.filing_id == filing_id, CategoryAssignment.parent_assignment_id.is_(None))
        ).all()
    )
    if not review_items:
        gaps.append(
            {
                "gap_key": "review:no_review_items",
                "gap_code": "no_review_items",
                "severity": GapSeverity.critical,
                "user_message": "No review items are available yet for this filing.",
                "suggested_action": "Process documents to generate candidate tax items.",
                "context_json": None,
            }
        )
        return gaps

    unresolved_items = [
        item.id
        for item in review_items
        if item.status in {ReviewItemStatus.candidate, ReviewItemStatus.marked_for_later}
    ]
    if unresolved_items:
        gaps.append(
            {
                "gap_key": "review:unresolved_items",
                "gap_code": "unresolved_review_items",
                "severity": GapSeverity.warning,
                "user_message": "Some extracted items still need user review.",
                "suggested_action": "Review, accept, override, or split the remaining candidate items.",
                "context_json": {"review_item_ids": unresolved_items},
            }
        )

    conflicted_items = [
        item.id for item in review_items if item.reconciliation_status == ReconciliationStatus.conflicted
    ]
    if conflicted_items:
        gaps.append(
            {
                "gap_key": "reconciliation:conflicted_items",
                "gap_code": "reconciliation_conflicts",
                "severity": GapSeverity.warning,
                "user_message": "Some reviewed values conflict across uploaded documents.",
                "suggested_action": "Inspect the conflicted review items and choose the correct value before calculation.",
                "context_json": {"review_item_ids": conflicted_items},
            }
        )

    unsupported_items = [
        item.id for item in review_items if item.reconciliation_status == ReconciliationStatus.unsupported
    ]
    if unsupported_items:
        gaps.append(
            {
                "gap_key": "reconciliation:unsupported_items",
                "gap_code": "unsupported_review_items",
                "severity": GapSeverity.warning,
                "user_message": "Some reviewed values are not corroborated by the expected supporting documents.",
                "suggested_action": "Upload supporting documents or manually confirm the unsupported values during review.",
                "context_json": {"review_item_ids": unsupported_items},
            }
        )

    accepted_or_finalized = [
        item
        for item in db.scalars(
            select(CategoryAssignment)
            .where(
                CategoryAssignment.filing_id == filing_id,
                CategoryAssignment.status.in_(
                    [
                        ReviewItemStatus.accepted,
                        ReviewItemStatus.overridden,
                    ]
                ),
            )
        ).all()
    ]
    review_signal_items = [
        item
        for item in review_items
        if item.status not in {ReviewItemStatus.rejected, ReviewItemStatus.split}
    ]
    if any(_item_category(item) == NormalizedTaxItemCategory.salary_income for item in review_signal_items):
        if not present_document_types.intersection(FORM16_TYPES):
            gaps.append(
                {
                    "gap_key": "documents:missing_form16",
                    "gap_code": "missing_form16",
                    "severity": GapSeverity.critical,
                    "user_message": "Salary-related data exists, but Form 16 is missing for this filing.",
                    "suggested_action": "Upload Form 16 so salary and TDS details can be verified before calculation.",
                    "context_json": None,
                }
            )

    if any(_item_category(item) == NormalizedTaxItemCategory.tds_credits for item in review_signal_items):
        if not present_document_types.intersection(FORM16_TYPES | FORM26AS_TYPES | AIS_TYPES):
            gaps.append(
                {
                    "gap_key": "documents:missing_tds_support",
                    "gap_code": "missing_tds_support",
                    "severity": GapSeverity.warning,
                    "user_message": "TDS-related entries are present, but no supporting Form 16, 26AS, or AIS document is available.",
                    "suggested_action": "Upload Form 16, Form 26AS, or AIS to support the claimed TDS credits.",
                    "context_json": None,
                }
            )

    if any(_item_category(item) == NormalizedTaxItemCategory.interest_income for item in review_signal_items):
        if not present_document_types.intersection(INTEREST_SUPPORT_TYPES):
            gaps.append(
                {
                    "gap_key": "documents:missing_interest_support",
                    "gap_code": "missing_interest_support",
                    "severity": GapSeverity.warning,
                    "user_message": "Interest income appears in the filing, but no bank statement, interest certificate, AIS, or 26AS support is present.",
                    "suggested_action": "Upload an interest certificate, bank statement, AIS, or Form 26AS to support the reported interest income.",
                    "context_json": None,
                }
            )

    if any(_item_category(item) == NormalizedTaxItemCategory.domestic_dividend_income for item in review_signal_items):
        if not present_document_types.intersection(DIVIDEND_SUPPORT_TYPES):
            gaps.append(
                {
                    "gap_key": "documents:missing_dividend_support",
                    "gap_code": "missing_dividend_support",
                    "severity": GapSeverity.warning,
                    "user_message": "Dividend income appears in the filing, but no AIS, dividend statement, or broker support is present.",
                    "suggested_action": "Upload AIS or the relevant dividend or broker statement to support the reported dividend income.",
                    "context_json": None,
                }
            )

    if any(_item_category(item) == NormalizedTaxItemCategory.capital_gains for item in review_signal_items):
        if not present_document_types.intersection(CAPITAL_GAINS_SUPPORT_TYPES):
            gaps.append(
                {
                    "gap_key": "documents:missing_capital_gains_support",
                    "gap_code": "missing_capital_gains_support",
                    "severity": GapSeverity.warning,
                    "user_message": "Capital gains appear in the filing, but no broker, capital gains statement, AIS, or equity-event support is present.",
                    "suggested_action": "Upload the relevant broker statement, capital gains statement, AIS, or equity compensation support before calculation.",
                    "context_json": None,
                }
            )

    proof_backed_deduction_items = [
        item
        for item in review_signal_items
        if _item_category(item) == NormalizedTaxItemCategory.deductions
        and item.description.lower() not in {"standard_deduction", "professional_tax"}
    ]
    if proof_backed_deduction_items:
        if not present_document_types.intersection(DEDUCTION_SUPPORT_TYPES):
            gaps.append(
                {
                    "gap_key": "documents:missing_deduction_proof",
                    "gap_code": "missing_deduction_proof",
                    "severity": GapSeverity.warning,
                    "user_message": "Deduction-related items are present, but no supporting proof document has been uploaded.",
                    "suggested_action": "Upload the relevant deduction proof, such as insurance, PPF/ELSS, donation, tuition, rent, or home loan documents.",
                    "context_json": None,
                }
            )

    foreign_related_items = [
        item
        for item in accepted_or_finalized
        if (item.final_category or item.suggested_category)
        in {
            NormalizedTaxItemCategory.foreign_dividend_income,
            NormalizedTaxItemCategory.capital_gains,
            NormalizedTaxItemCategory.other_sources,
        }
        and item.currency_code not in (None, "INR")
    ]
    if foreign_related_items:
        missing_conversion_ids = [
            item.id for item in foreign_related_items if item.amount_in_inr is None
        ]
        if missing_conversion_ids:
            gaps.append(
                {
                    "gap_key": "foreign:missing_conversion_basis",
                    "gap_code": "missing_conversion_basis",
                    "severity": GapSeverity.warning,
                    "user_message": "Foreign-currency items still need INR conversion or conversion-basis review.",
                    "suggested_action": "Add or confirm INR conversion details for foreign-currency items.",
                    "context_json": {"review_item_ids": missing_conversion_ids},
                }
            )

    foreign_events = list(
        db.scalars(
            select(ForeignIncomeEvent)
            .join(Document, Document.id == ForeignIncomeEvent.document_id)
            .where(Document.filing_id == filing_id)
        ).all()
    )
    for event in foreign_events:
        missing_parts = []
        if not event.country:
            missing_parts.append("country")
        if not event.broker_platform:
            missing_parts.append("broker_platform")
        if not event.security_identifier:
            missing_parts.append("security_identifier")
        if missing_parts:
            gaps.append(
                {
                    "gap_key": f"foreign:event_metadata:{event.id}",
                    "gap_code": "missing_foreign_event_details",
                    "severity": GapSeverity.warning,
                    "user_message": "A foreign income event is missing some supporting metadata.",
                    "suggested_action": "Review and complete the foreign event details before calculation.",
                    "context_json": {"foreign_event_id": event.id, "missing_fields": missing_parts},
                }
            )

    return gaps


def _ensure_review_session(db: Session, filing_id: str) -> None:
    existing = db.scalar(
        select(ReviewSession).where(ReviewSession.filing_id == filing_id, ReviewSession.status == "active").limit(1)
    )
    if existing is None:
        db.add(ReviewSession(id=str(uuid4()), filing_id=filing_id, status="active"))


def _touch_review_session(db: Session, filing_id: str) -> None:
    session = db.scalar(
        select(ReviewSession).where(ReviewSession.filing_id == filing_id, ReviewSession.status == "active").limit(1)
    )
    if session is None:
        session = ReviewSession(id=str(uuid4()), filing_id=filing_id, status="active")
        db.add(session)
    session.last_activity_at = datetime.utcnow()


def _record_override(
    db: Session,
    assignment: CategoryAssignment,
    override_type: str,
    from_category: NormalizedTaxItemCategory | None,
    to_category: NormalizedTaxItemCategory | None,
    reason: str | None,
    payload_json: dict | list | None,
) -> None:
    db.add(
        ManualOverride(
            id=str(uuid4()),
            category_assignment_id=assignment.id,
            override_type=override_type,
            from_category=from_category,
            to_category=to_category,
            reason=reason,
            payload_json=payload_json,
        )
    )


def _get_assignment_or_raise(db: Session, assignment_id: str) -> CategoryAssignment:
    assignment = db.get(CategoryAssignment, assignment_id)
    if assignment is None:
        raise ValueError("Review item not found")
    return assignment


def _item_category(item: CategoryAssignment) -> NormalizedTaxItemCategory:
    return item.final_category or item.suggested_category


def _present_document_types(documents: list[Document]) -> set[str]:
    return {
        document.document_type.strip().lower()
        for document in documents
        if document.document_type is not None and document.document_type.strip()
    }


def _refresh_reconciliation_state(db: Session, filing_id: str) -> None:
    assignments = list(
        db.scalars(
            select(CategoryAssignment)
            .where(CategoryAssignment.filing_id == filing_id)
            .options(
                selectinload(CategoryAssignment.normalized_tax_item).selectinload(NormalizedTaxItem.document),
            )
        ).all()
    )
    active_items = [
        item
        for item in assignments
        if item.status not in {ReviewItemStatus.rejected, ReviewItemStatus.split}
    ]
    buckets: dict[tuple[NormalizedTaxItemCategory, str], list[CategoryAssignment]] = defaultdict(list)
    for item in active_items:
        buckets[(_item_category(item), _reconciliation_key(item))].append(item)

    for item in assignments:
        status, context = _reconciliation_for_item(item, buckets)
        item.reconciliation_status = status
        item.reconciliation_context_json = context


def _reconciliation_for_item(
    item: CategoryAssignment,
    buckets: dict[tuple[NormalizedTaxItemCategory, str], list[CategoryAssignment]],
) -> tuple[ReconciliationStatus, dict[str, object]]:
    category = _item_category(item)
    key = _reconciliation_key(item)
    document_type = _document_type_for_assignment(item)
    authoritative_sources = _authoritative_sources_for_category(category)
    peers = [
        peer
        for peer in buckets.get((category, key), [])
        if peer.id != item.id and _document_type_for_assignment(peer) != document_type
    ]
    matching_peers = [
        peer
        for peer in peers
        if _amounts_align(item.amount, peer.amount)
    ]
    conflicting_peers = [
        peer
        for peer in peers
        if peer.amount is not None and item.amount is not None and not _amounts_align(item.amount, peer.amount)
    ]

    context = {
        "reconciliation_key": key,
        "document_type": document_type,
        "matched_review_item_ids": [peer.id for peer in matching_peers],
        "conflicted_review_item_ids": [peer.id for peer in conflicting_peers],
        "authoritative_document_types": sorted(authoritative_sources),
        "peer_document_types": sorted({_document_type_for_assignment(peer) for peer in peers if _document_type_for_assignment(peer)}),
    }

    if item.status == ReviewItemStatus.rejected:
        return ReconciliationStatus.unverified, context

    if matching_peers:
        return ReconciliationStatus.supported, context

    if conflicting_peers:
        return ReconciliationStatus.conflicted, context

    if _requires_authoritative_support(category):
        if document_type not in authoritative_sources and not matching_peers:
            return ReconciliationStatus.unsupported, context

    return ReconciliationStatus.unverified, context


def _reconciliation_key(item: CategoryAssignment) -> str:
    category = _item_category(item)
    description = (item.description or "").strip().lower()
    if category == NormalizedTaxItemCategory.tds_credits:
        return "tds"
    if category == NormalizedTaxItemCategory.interest_income:
        if description in {"interest_income", "income_paid"}:
            return "interest_income"
        return description or "interest_income"
    if category == NormalizedTaxItemCategory.salary_income:
        if description in {"gross_salary", "salary_income"}:
            return "salary_income"
        return description or "salary_income"
    if category == NormalizedTaxItemCategory.deductions:
        return description or "deductions"
    return description or category.value


def _document_type_for_assignment(item: CategoryAssignment) -> str | None:
    normalized = item.normalized_tax_item
    if normalized is None or normalized.document is None or normalized.document.document_type is None:
        return None
    document_type = normalized.document.document_type.strip().lower()
    return document_type or None


def _authoritative_sources_for_category(category: NormalizedTaxItemCategory) -> set[str]:
    if category == NormalizedTaxItemCategory.tds_credits:
        return AUTHORITATIVE_TDS_TYPES
    if category == NormalizedTaxItemCategory.salary_income:
        return AUTHORITATIVE_SALARY_TYPES
    if category == NormalizedTaxItemCategory.interest_income:
        return AUTHORITATIVE_INTEREST_TYPES
    if category == NormalizedTaxItemCategory.domestic_dividend_income:
        return DIVIDEND_SUPPORT_TYPES
    if category == NormalizedTaxItemCategory.capital_gains:
        return CAPITAL_GAINS_SUPPORT_TYPES
    if category == NormalizedTaxItemCategory.deductions:
        return DEDUCTION_SUPPORT_TYPES
    return set()


def _requires_authoritative_support(category: NormalizedTaxItemCategory) -> bool:
    return bool(_authoritative_sources_for_category(category))


def _amounts_align(left: Decimal | None, right: Decimal | None) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= AMOUNT_TOLERANCE
