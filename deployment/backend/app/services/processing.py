from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Document,
    DocumentCompletenessState,
    DocumentProcessingStatus,
    DocumentValidationResult,
    DocumentValidationState,
    DocumentVersion,
    FieldProvenance,
    Filing,
    ForeignIncomeEvent,
    NormalizedTaxItem,
    NormalizedTaxItemCategory,
    ParsedField,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    RawExtraction,
)


JOB_SEQUENCE = [
    ProcessingJobType.validate_document,
    ProcessingJobType.parse_document,
    ProcessingJobType.extract_fields,
    ProcessingJobType.normalize_tax_items,
]

TAX_KEYWORDS = {
    "form16",
    "form 16",
    "26as",
    "ais",
    "tis",
    "salary",
    "tax",
    "tds",
    "dividend",
    "interest",
    "capital gains",
    "broker",
    "rsu",
    "esop",
    "foreign",
    "withholding",
    "itr",
}

FOREIGN_HINTS = {
    "foreign",
    "broker",
    "withholding",
    "country",
    "security",
    "rsu",
    "esop",
    "dividend",
    "vesting",
}

CURRENCY_PATTERN = re.compile(r"\b(INR|USD|EUR|GBP|SGD|AED|JPY)\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
AMOUNT_PATTERN = re.compile(r"[-+]?\d[\d,]*(?:\.\d{1,2})?")
PRINTABLE_RUN_PATTERN = re.compile(r"[A-Za-z0-9:/\-\s,.()]{4,}")
STRUCTURED_CONTENT_FORMATS = {"json", "xml", "csv", "xlsx"}
OCR_CONTENT_FORMAT = "ocr_text"
PDF_CONTENT_FORMAT = "pdf_text"
PAGE_MARKER_PATTERN = re.compile(r"^\[page:(\d+)\]$")

DOCUMENT_TYPE_PATTERNS: dict[str, tuple[str, ...]] = {
    "form16": ("form 16", "form16", "part a", "part b", "salary certificate"),
    "form26as": ("form 26as", "26as", "tax credit statement", "part a1", "part a2"),
    "ais": ("annual information statement", "ais", "taxpayer information summary", "tis"),
    "salary_slip": ("salary slip", "payslip", "pay slip", "earnings", "deductions"),
    "interest_certificate": ("interest certificate", "interest paid", "savings interest", "fixed deposit interest"),
    "bank_statement": ("bank statement", "account statement", "statement period", "interest_period", "account_holder_name", "issuer_name"),
    "capital_gains_statement": ("capital gains", "short term capital gain", "long term capital gain"),
    "broker_statement": ("broker statement", "contract note", "trading statement"),
    "dividend_statement": ("dividend statement", "dividend advice"),
    "foreign_dividend_statement": ("foreign dividend", "withholding tax", "broker platform"),
    "rsu_statement": ("rsu", "restricted stock unit", "vesting"),
    "esop_statement": ("esop", "employee stock option"),
    "rent_receipt": ("rent receipt", "landlord", "house rent"),
    "home_loan_certificate": ("home loan", "interest certificate", "principal repaid"),
    "insurance_premium_proof": ("insurance premium", "life insurance", "premium paid"),
    "ppf_elss_proof": ("ppf", "elss", "tax saver", "80c investment"),
    "donation_receipt": ("donation", "80g", "receipt no"),
    "tuition_fee_receipt": ("tuition fee", "school fee", "education fee"),
    "medical_insurance_document": ("medical insurance", "health insurance", "80d"),
}

FIELD_ALIAS_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("assessment_year", ("assessment year", "ay")),
    ("financial_year", ("financial year", "fy")),
    ("employer_name", ("employer", "employer name", "deductor name")),
    ("employee_name", ("employee", "employee name", "assessee name")),
    ("account_holder_name", ("account holder", "account holder name", "customer name")),
    ("issuer_name", ("issuer", "issuer name", "bank name", "institution name")),
    ("account_number_masked", ("account number", "account no", "masked account number")),
    ("pan", ("pan", "pan no", "pan number")),
    ("tan", ("tan", "tan no", "tan number")),
    ("gross_salary", ("gross salary", "gross total salary", "income under the head salaries", "salary as per provisions contained in section 17(1)", "taxable salary")),
    ("basic_salary", ("basic salary", "basic pay")),
    ("salary_income", ("salary income", "net salary")),
    ("net_pay", ("net pay", "take home", "take-home", "take home pay")),
    ("payslip_month", ("salary month", "pay month", "month")),
    ("payslip_period", ("pay period", "salary period")),
    ("interest_period", ("interest period", "deposit period", "statement period")),
    ("standard_deduction", ("standard deduction",)),
    ("professional_tax", ("professional tax",)),
    ("house_rent_allowance", ("hra", "house rent allowance")),
    ("special_allowance", ("special allowance",)),
    ("other_allowance", ("other allowance", "other earnings")),
    ("bonus", ("bonus", "performance bonus")),
    ("provident_fund_employee", ("employee pf", "employee provident fund", "epf employee")),
    ("provident_fund_employer", ("employer pf", "employer provident fund", "epf employer")),
    ("interest_income", ("interest income", "bank interest", "savings interest", "deposit interest", "interest paid")),
    ("dividend_income", ("dividend income", "domestic dividend")),
    ("foreign_dividend_amount", ("foreign dividend", "dividend amount", "gross dividend")),
    ("short_term_capital_gain", ("short term capital gain", "stcg", "short-term capital gain")),
    ("long_term_capital_gain", ("long term capital gain", "ltcg", "long-term capital gain")),
    ("capital_gains_total", ("capital gains total", "total capital gains", "net capital gain")),
    ("sale_proceeds", ("sale proceeds", "gross sale value", "sell value")),
    ("cost_basis", ("cost basis", "purchase cost", "acquisition cost", "cost of acquisition")),
    ("security_name", ("security name", "stock name", "company name", "instrument")),
    ("quantity", ("quantity", "units", "shares")),
    ("transaction_type", ("transaction type", "event type", "activity type")),
    ("withholding_amount", ("withholding", "withholding tax", "foreign tax withheld", "tax withheld")),
    ("tax_deducted", ("tax deducted", "tds", "total tds", "tax deducted at source", "tds deducted", "tax credit")),
    ("tax_collected", ("tax collected", "tcs")),
    ("deductor_name", ("deductor", "deductor name")),
    ("income_paid", ("income paid", "amount paid", "payment amount")),
    ("deduction_80c", ("80c", "section 80c")),
    ("deduction_80d", ("80d", "section 80d")),
    ("deduction_housing_loan", ("housing loan", "home loan interest", "section 24")),
    ("investment_amount", ("investment amount", "amount invested", "deposit amount")),
    ("premium_paid", ("premium paid", "insurance premium", "medical insurance premium")),
    ("donation_amount", ("donation amount", "amount donated")),
    ("tuition_fee_amount", ("tuition fee", "education fee", "school fee")),
    ("rent_paid", ("rent paid", "monthly rent")),
    ("home_loan_interest", ("home loan interest", "interest paid on housing loan")),
    ("advance_tax", ("advance tax",)),
    ("self_assessment_tax", ("self assessment tax", "self-assessment tax")),
    ("broker_platform", ("broker platform", "broker", "platform")),
    ("country", ("country", "source country")),
    ("security_identifier", ("security identifier", "isin", "ticker", "symbol")),
    ("event_date", ("event date", "transaction date", "dividend date", "credit date")),
]


@dataclass
class ParsedPayload:
    content_format: str
    payload_json: dict | list | None
    text_content: str | None
    source_type: str


def _job_order_expression():
    return case(
        (ProcessingJob.job_type == ProcessingJobType.validate_document, 1),
        (ProcessingJob.job_type == ProcessingJobType.parse_document, 2),
        (ProcessingJob.job_type == ProcessingJobType.run_ocr, 3),
        (ProcessingJob.job_type == ProcessingJobType.extract_fields, 4),
        (ProcessingJob.job_type == ProcessingJobType.normalize_tax_items, 5),
        else_=99,
    )


def get_document_with_phase3_relations(db: Session, document_id: str) -> Document | None:
    return db.scalar(
        select(Document)
        .where(Document.id == document_id)
        .options(
            selectinload(Document.filing),
            selectinload(Document.versions).selectinload(DocumentVersion.storage_ref),
            selectinload(Document.processing_jobs),
            selectinload(Document.validation_results),
            selectinload(Document.parsed_fields),
            selectinload(Document.normalized_tax_items),
            selectinload(Document.foreign_income_events),
        )
    )


def latest_document_version(document: Document):
    if not document.versions:
        raise ValueError("Document has no versions")
    return max(document.versions, key=lambda version: version.version_number)


def clear_phase3_outputs_for_version(db: Session, document_version_id: str) -> None:
    parsed_field_ids = list(
        db.scalars(select(ParsedField.id).where(ParsedField.document_version_id == document_version_id)).all()
    )
    if parsed_field_ids:
        db.execute(delete(FieldProvenance).where(FieldProvenance.parsed_field_id.in_(parsed_field_ids)))
    db.execute(delete(ForeignIncomeEvent).where(ForeignIncomeEvent.document_version_id == document_version_id))
    db.execute(delete(NormalizedTaxItem).where(NormalizedTaxItem.document_version_id == document_version_id))
    db.execute(delete(ParsedField).where(ParsedField.document_version_id == document_version_id))
    db.execute(delete(RawExtraction).where(RawExtraction.document_version_id == document_version_id))
    db.execute(delete(DocumentValidationResult).where(DocumentValidationResult.document_version_id == document_version_id))
    db.execute(delete(ProcessingJob).where(ProcessingJob.document_version_id == document_version_id))


def enqueue_phase3_jobs(db: Session, document: Document) -> list[ProcessingJob]:
    version = latest_document_version(document)
    jobs: list[ProcessingJob] = []
    for job_type in JOB_SEQUENCE:
        job = ProcessingJob(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            job_type=job_type,
            status=ProcessingJobStatus.pending,
            updated_at=datetime.utcnow(),
        )
        db.add(job)
        jobs.append(job)
    document.processing_status = (
        DocumentProcessingStatus.duplicate if document.is_duplicate else DocumentProcessingStatus.queued
    )
    document.updated_at = datetime.utcnow()
    db.flush()
    return jobs


def run_document_pipeline(db: Session, document_id: str) -> list[ProcessingJob]:
    completed_jobs: list[ProcessingJob] = []
    while True:
        job = db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id, ProcessingJob.status == ProcessingJobStatus.pending)
            .order_by(_job_order_expression(), ProcessingJob.created_at.asc(), ProcessingJob.id.asc())
            .limit(1)
        )
        if job is None:
            break
        completed_jobs.append(run_processing_job(db, job.id))
    return completed_jobs


def run_next_pending_job(db: Session) -> ProcessingJob | None:
    job = db.scalar(
        select(ProcessingJob)
        .where(ProcessingJob.status == ProcessingJobStatus.pending)
        .order_by(_job_order_expression(), ProcessingJob.created_at.asc(), ProcessingJob.id.asc())
        .limit(1)
    )
    if job is None:
        return None
    return run_processing_job(db, job.id)


def run_processing_job(db: Session, job_id: str) -> ProcessingJob:
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id))
    if job is None:
        raise ValueError("Processing job not found")

    document = db.scalar(
        select(Document)
        .where(Document.id == job.document_id)
        .options(selectinload(Document.filing), selectinload(Document.versions).selectinload(DocumentVersion.storage_ref))
    )
    if document is None:
        raise ValueError("Document not found for processing job")

    version = next((item for item in document.versions if item.id == job.document_version_id), None)
    if version is None or version.storage_ref is None:
        raise ValueError("Document version storage is missing")

    job.status = ProcessingJobStatus.processing
    job.attempt_count += 1
    job.started_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()
    if not document.is_duplicate:
        document.processing_status = DocumentProcessingStatus.processing
    db.commit()

    try:
        if job.job_type == ProcessingJobType.validate_document:
            _run_validation_stage(db, job, document, version, version.storage_ref.storage_path)
        elif _should_skip_downstream_processing(db, version.id):
            pass
        elif job.job_type == ProcessingJobType.parse_document:
            _run_parse_stage(db, job, document, version, version.storage_ref.storage_path)
        elif job.job_type == ProcessingJobType.run_ocr:
            _run_ocr_stage(db, job, document, version, version.storage_ref.storage_path)
        elif job.job_type == ProcessingJobType.extract_fields:
            _run_extract_fields_stage(db, job, document, version)
        elif job.job_type == ProcessingJobType.normalize_tax_items:
            _run_normalization_stage(db, job, document, version)
        else:
            raise ValueError(f"Unsupported job type: {job.job_type}")
        if job.status == ProcessingJobStatus.processing:
            job.status = ProcessingJobStatus.completed
        job.completed_at = datetime.utcnow()
        job.error_message = None
    except Exception as exc:
        job.status = ProcessingJobStatus.failed
        job.completed_at = datetime.utcnow()
        job.error_message = str(exc)
    finally:
        job.updated_at = datetime.utcnow()
        _refresh_document_processing_status(db, document.id)
        db.commit()

    refreshed = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job.id))
    if refreshed is None:
        raise ValueError("Processing job disappeared after execution")
    return refreshed


def _should_skip_downstream_processing(db: Session, document_version_id: str) -> bool:
    validation = db.scalar(
        select(DocumentValidationResult)
        .where(DocumentValidationResult.document_version_id == document_version_id)
        .order_by(DocumentValidationResult.created_at.desc())
        .limit(1)
    )
    if validation is None:
        return False
    return validation.validation_state in {
        DocumentValidationState.duplicate,
        DocumentValidationState.not_relevant,
        DocumentValidationState.unsupported,
        DocumentValidationState.corrupted_unreadable,
    }


def build_processing_summary(db: Session, document: Document) -> dict[str, object]:
    version = latest_document_version(document)
    jobs = list(
        db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document.id, ProcessingJob.document_version_id == version.id)
            .order_by(ProcessingJob.created_at.asc())
        ).all()
    )
    validation = db.scalar(
        select(DocumentValidationResult)
        .where(DocumentValidationResult.document_version_id == version.id)
        .order_by(DocumentValidationResult.created_at.desc())
        .limit(1)
    )
    parsed_fields_count = db.scalar(
        select(func.count()).select_from(ParsedField).where(ParsedField.document_version_id == version.id)
    ) or 0
    normalized_count = db.scalar(
        select(func.count()).select_from(NormalizedTaxItem).where(NormalizedTaxItem.document_version_id == version.id)
    ) or 0
    foreign_count = db.scalar(
        select(func.count()).select_from(ForeignIncomeEvent).where(ForeignIncomeEvent.document_version_id == version.id)
    ) or 0
    return {
        "document_id": document.id,
        "document_version_id": version.id,
        "jobs": jobs,
        "validation_result": validation,
        "parsed_fields_count": int(parsed_fields_count),
        "normalized_tax_items_count": int(normalized_count),
        "foreign_income_events_count": int(foreign_count),
    }


def _refresh_document_processing_status(db: Session, document_id: str) -> None:
    document = db.get(Document, document_id)
    if document is None:
        return
    if document.is_duplicate:
        document.processing_status = DocumentProcessingStatus.duplicate
        document.updated_at = datetime.utcnow()
        return

    latest_version_id = db.scalar(
        select(DocumentVersion.id)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    if latest_version_id is None:
        document.processing_status = DocumentProcessingStatus.uploaded
        document.updated_at = datetime.utcnow()
        return

    jobs = list(
        db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.document_id == document_id,
                ProcessingJob.document_version_id == latest_version_id,
            )
        ).all()
    )
    if not jobs:
        document.processing_status = DocumentProcessingStatus.uploaded
    elif any(job.status == ProcessingJobStatus.failed for job in jobs):
        document.processing_status = DocumentProcessingStatus.failed
    elif any(job.status == ProcessingJobStatus.processing for job in jobs):
        document.processing_status = DocumentProcessingStatus.processing
    elif any(job.status == ProcessingJobStatus.needs_review for job in jobs):
        document.processing_status = DocumentProcessingStatus.needs_review
    elif all(job.status == ProcessingJobStatus.completed for job in jobs):
        document.processing_status = DocumentProcessingStatus.completed
    else:
        document.processing_status = DocumentProcessingStatus.queued
    document.updated_at = datetime.utcnow()


def _run_validation_stage(
    db: Session,
    job: ProcessingJob,
    document: Document,
    version: DocumentVersion,
    storage_path: str,
) -> None:
    file_bytes = Path(storage_path).read_bytes()
    text_probe = _extract_text_probe(file_bytes, version.file_extension)
    inferred_document_type = _set_inferred_document_type(document, version, text_probe)
    validation_state = DocumentValidationState.relevant
    is_relevant = _looks_tax_related(document, version, text_probe)
    year_label, year_matches = _detect_year_match(document.filing, text_probe)
    parseable = bool(file_bytes)
    completeness_state = DocumentCompletenessState.complete if file_bytes else DocumentCompletenessState.incomplete
    reason_parts: list[str] = []

    if document.is_duplicate:
        validation_state = DocumentValidationState.duplicate
        reason_parts.append("This upload matches an existing document checksum for the filing.")
    elif not parseable:
        validation_state = DocumentValidationState.corrupted_unreadable
        completeness_state = DocumentCompletenessState.incomplete
        reason_parts.append("The file could not be read from local storage.")
    elif version.file_extension == "pdf" and not text_probe.strip():
        validation_state = DocumentValidationState.possibly_relevant
        completeness_state = DocumentCompletenessState.partial
        reason_parts.append("The PDF has no native text layer. OCR fallback will be used.")
    elif not is_relevant:
        validation_state = DocumentValidationState.not_relevant
        reason_parts.append("The file does not currently look like a tax-relevant document.")
    elif year_matches is False:
        validation_state = DocumentValidationState.possibly_relevant
        reason_parts.append("The document may belong to a different financial or assessment year.")
    else:
        reason_parts.append("The document looks relevant and locally parseable for Phase 3 processing.")

    if inferred_document_type:
        reason_parts.append(f"Detected document type: {inferred_document_type}.")
    if year_label:
        reason_parts.append(f"Detected year context: {year_label}.")
    if not reason_parts:
        reason_parts.append("Validation completed with no blocking issues detected.")

    db.add(
        DocumentValidationResult(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            processing_job_id=job.id,
            validation_state=validation_state,
            completeness_state=completeness_state,
            is_relevant=is_relevant,
            year_matches_filing=year_matches,
            parseable=parseable,
            duplicate_detected=document.is_duplicate,
            conflict_detected=False,
            detected_tax_year_label=year_label,
            plain_language_reason=" ".join(reason_parts),
        )
    )


def _run_parse_stage(
    db: Session,
    job: ProcessingJob,
    document: Document,
    version: DocumentVersion,
    storage_path: str,
) -> None:
    file_bytes = Path(storage_path).read_bytes()
    parsed = _parse_file_bytes(file_bytes, version.file_extension)
    _set_inferred_document_type(document, version, parsed.text_content or "")
    db.add(
        RawExtraction(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            processing_job_id=job.id,
            extraction_stage="parse",
            content_format=parsed.content_format,
            payload_json=parsed.payload_json,
            text_content=parsed.text_content,
        )
    )
    if version.file_extension == "pdf" and not _parsed_payload_has_meaningful_text(parsed):
        if not _ocr_job_exists(db, document.id, version.id):
            db.add(
                ProcessingJob(
                    id=str(uuid4()),
                    document_id=document.id,
                    document_version_id=version.id,
                    job_type=ProcessingJobType.run_ocr,
                    status=ProcessingJobStatus.pending,
                    updated_at=datetime.utcnow(),
                )
            )


def _run_ocr_stage(
    db: Session,
    job: ProcessingJob,
    document: Document,
    version: DocumentVersion,
    storage_path: str,
) -> None:
    file_bytes = Path(storage_path).read_bytes()
    parsed = _ocr_pdf_file(file_bytes)
    inferred_document_type = _set_inferred_document_type(document, version, parsed.text_content or "")
    db.add(
        RawExtraction(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            processing_job_id=job.id,
            extraction_stage="ocr",
            content_format=parsed.content_format,
            payload_json=parsed.payload_json,
            text_content=parsed.text_content,
        )
    )
    if not _parsed_payload_has_meaningful_text(parsed):
        _record_validation_result(
            db=db,
            document=document,
            version=version,
            processing_job_id=job.id,
            text_probe=parsed.text_content or "",
            validation_state=DocumentValidationState.needs_user_review,
            completeness_state=DocumentCompletenessState.partial,
            plain_language_reason="OCR completed, but no reliable text could be extracted from the PDF.",
            is_relevant=False,
            parseable=True,
            duplicate_detected=document.is_duplicate,
        )
        job.status = ProcessingJobStatus.needs_review
        return

    detected_year_label, year_matches = _detect_year_match(document.filing, parsed.text_content or "")
    is_relevant = _looks_tax_related(document, version, parsed.text_content or "")
    validation_state = DocumentValidationState.relevant if is_relevant else DocumentValidationState.possibly_relevant
    reason = "OCR fallback extracted text from the PDF and Phase 3 processing continued successfully."
    if not is_relevant:
        reason = "OCR fallback extracted text, but the document still needs review for tax relevance."
    if inferred_document_type:
        reason = f"{reason} Detected document type: {inferred_document_type}."
    if detected_year_label:
        reason = f"{reason} Detected year context: {detected_year_label}."
    _record_validation_result(
        db=db,
        document=document,
        version=version,
        processing_job_id=job.id,
        text_probe=parsed.text_content or "",
        validation_state=validation_state,
        completeness_state=DocumentCompletenessState.complete,
        plain_language_reason=reason,
        is_relevant=is_relevant,
        parseable=True,
        duplicate_detected=document.is_duplicate,
        year_matches_filing=year_matches,
        detected_tax_year_label=detected_year_label,
    )


def _run_extract_fields_stage(
    db: Session,
    job: ProcessingJob,
    document: Document,
    version: DocumentVersion,
) -> None:
    del job
    raw_extractions = list(
        db.scalars(
            select(RawExtraction)
            .where(RawExtraction.document_version_id == version.id)
            .order_by(RawExtraction.created_at.asc())
        ).all()
    )
    for raw_extraction in raw_extractions:
        fields = _fields_from_raw_extraction(raw_extraction)
        for field_name, field_value, value_type, locator, page_number in fields:
            parsed_field = ParsedField(
                id=str(uuid4()),
                document_id=document.id,
                document_version_id=version.id,
                raw_extraction_id=raw_extraction.id,
                field_name=field_name,
                field_value_text=field_value,
                value_type=value_type,
                confidence=_confidence_for_source(raw_extraction.content_format),
                source_locator=locator,
                page_number=page_number,
                currency_code=_extract_currency_code(field_value),
                event_date=_parse_date(field_value),
            )
            db.add(parsed_field)
            db.flush()
            db.add(
                FieldProvenance(
                    id=str(uuid4()),
                    parsed_field_id=parsed_field.id,
                    raw_extraction_id=raw_extraction.id,
                    source_type=raw_extraction.content_format,
                    source_locator=locator,
                    source_snippet=field_value[:500],
                )
            )


def _run_normalization_stage(
    db: Session,
    job: ProcessingJob,
    document: Document,
    version: DocumentVersion,
) -> None:
    fields = list(
        db.scalars(
            select(ParsedField)
            .where(ParsedField.document_version_id == version.id)
            .order_by(ParsedField.created_at.asc())
        ).all()
    )
    field_map = {field.field_name.lower(): field for field in fields}
    for field in fields:
        item = _normalized_item_for_field(field, document.document_type)
        if item is None:
            continue
        normalized = NormalizedTaxItem(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            processing_job_id=job.id,
            source_parsed_field_id=field.id,
            category=item["category"],
            subcategory=item["subcategory"],
            description=item["description"],
            amount=item["amount"],
            currency_code=item["currency_code"],
            amount_in_inr=item["amount_in_inr"],
            event_date=field.event_date,
            confidence=field.confidence,
            review_status="candidate",
        )
        db.add(normalized)
        db.flush()
        foreign_event = _foreign_income_event_for_item(document, version.id, normalized, field, field_map)
        if foreign_event is not None:
            db.add(foreign_event)


def _extract_text_probe(file_bytes: bytes, extension: str) -> str:
    try:
        parsed = _parse_file_bytes(file_bytes, extension)
        return parsed.text_content or ""
    except Exception:
        return ""


def _looks_tax_related(document: Document, version, text_probe: str) -> bool:
    if _infer_document_type(document, version, text_probe) is not None:
        return True
    haystacks = [
        (document.document_type or "").lower(),
        (document.source or "").lower(),
        version.original_filename.lower(),
        text_probe.lower(),
    ]
    return any(keyword in haystack for keyword in TAX_KEYWORDS for haystack in haystacks)


def _detect_year_match(filing: Filing | None, text_probe: str) -> tuple[str | None, bool | None]:
    if filing is None:
        return None, None
    found_years = {int(match) for match in YEAR_PATTERN.findall(text_probe)}
    if not found_years:
        return None, None
    valid_years = {
        filing.assessment_year,
        filing.financial_year_start,
        filing.financial_year_end,
    }
    year_matches = bool(found_years.intersection(valid_years))
    label = ", ".join(str(year) for year in sorted(found_years))
    return label, year_matches


def _infer_document_type(document: Document, version: DocumentVersion, text_probe: str) -> str | None:
    explicit = (document.document_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if explicit:
        return explicit

    normalized_text_probe = text_probe.lower()
    for document_type in DOCUMENT_TYPE_PATTERNS:
        exact_markers = {
            f'"document_type": "{document_type}"',
            f'"document_type":"{document_type}"',
            f'"document type": "{document_type}"',
            f'"document_type": "{document_type.replace("_", " ")}"',
            f'"document_type":"{document_type.replace("_", " ")}"',
        }
        if any(marker in normalized_text_probe for marker in exact_markers):
            return document_type

    haystacks = [
        (version.original_filename or "").lower(),
        (document.source or "").lower(),
        normalized_text_probe,
    ]
    for document_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
        normalized_patterns = set(patterns) | {document_type, document_type.replace("_", " ")}
        if any(pattern in haystack for haystack in haystacks for pattern in normalized_patterns):
            return document_type
    return None


def _set_inferred_document_type(document: Document, version: DocumentVersion, text_probe: str) -> str | None:
    inferred = _infer_document_type(document, version, text_probe)
    if inferred is not None and not document.document_type:
        document.document_type = inferred
    return inferred


def _canonicalize_field_name(field_name: str) -> str:
    normalized = re.sub(r"[\s\-\/]+", "_", field_name.strip().lower())
    normalized = re.sub(r"[^a-z0-9_.\[\]_]", "", normalized)
    last_segment = normalized.split(".")[-1]
    last_segment = re.sub(r"\[\d+\]", "", last_segment)
    for canonical_name, patterns in FIELD_ALIAS_PATTERNS:
        if last_segment == canonical_name:
            return canonical_name
        if any(_alias_matches(last_segment, pattern) for pattern in patterns):
            return canonical_name
    return normalized or "value"


def _alias_matches(last_segment: str, pattern: str) -> bool:
    normalized_segment = last_segment.replace("_", " ").strip()
    normalized_pattern = pattern.replace("_", " ").strip().lower()
    if normalized_segment == normalized_pattern:
        return True

    segment_tokens = normalized_segment.split()
    pattern_tokens = normalized_pattern.split()

    if len(pattern_tokens) == 1:
        return normalized_pattern in segment_tokens

    segment_phrase = f" {' '.join(segment_tokens)} "
    pattern_phrase = f" {' '.join(pattern_tokens)} "
    return pattern_phrase in segment_phrase


def _document_category_hints(document_type: str | None) -> set[NormalizedTaxItemCategory]:
    if document_type == "form16":
        return {NormalizedTaxItemCategory.salary_income, NormalizedTaxItemCategory.tds_credits}
    if document_type == "salary_slip":
        return {
            NormalizedTaxItemCategory.salary_income,
            NormalizedTaxItemCategory.tds_credits,
            NormalizedTaxItemCategory.deductions,
        }
    if document_type in {"interest_certificate", "bank_statement"}:
        return {
            NormalizedTaxItemCategory.interest_income,
            NormalizedTaxItemCategory.tds_credits,
        }
    if document_type in {"broker_statement", "capital_gains_statement"}:
        return {
            NormalizedTaxItemCategory.capital_gains,
            NormalizedTaxItemCategory.domestic_dividend_income,
            NormalizedTaxItemCategory.foreign_dividend_income,
            NormalizedTaxItemCategory.other_sources,
        }
    if document_type == "dividend_statement":
        return {
            NormalizedTaxItemCategory.domestic_dividend_income,
            NormalizedTaxItemCategory.other_sources,
        }
    if document_type in {
        "insurance_premium_proof",
        "ppf_elss_proof",
        "donation_receipt",
        "tuition_fee_receipt",
        "medical_insurance_document",
        "rent_receipt",
        "home_loan_certificate",
    }:
        return {NormalizedTaxItemCategory.deductions}
    if document_type == "form26as":
        return {
            NormalizedTaxItemCategory.tds_credits,
            NormalizedTaxItemCategory.interest_income,
            NormalizedTaxItemCategory.other_sources,
        }
    if document_type == "ais":
        return {
            NormalizedTaxItemCategory.salary_income,
            NormalizedTaxItemCategory.interest_income,
            NormalizedTaxItemCategory.tds_credits,
            NormalizedTaxItemCategory.domestic_dividend_income,
            NormalizedTaxItemCategory.capital_gains,
            NormalizedTaxItemCategory.other_sources,
        }
    return set()


def _parse_file_bytes(file_bytes: bytes, extension: str) -> ParsedPayload:
    if extension == "json":
        payload = json.loads(file_bytes.decode("utf-8"))
        return ParsedPayload(
            content_format="json",
            payload_json=payload,
            text_content=json.dumps(payload, indent=2, ensure_ascii=True),
            source_type="structured_file",
        )
    if extension == "xml":
        root = ET.fromstring(file_bytes)
        payload = _xml_element_to_dict(root)
        text_parts = [text.strip() for text in root.itertext() if text and text.strip()]
        return ParsedPayload(
            content_format="xml",
            payload_json=payload,
            text_content="\n".join(text_parts),
            source_type="structured_file",
        )
    if extension == "csv":
        decoded = _decode_text(file_bytes)
        rows = _parse_csv_rows(decoded)
        return ParsedPayload(
            content_format="csv",
            payload_json=rows,
            text_content=_structured_payload_text(rows),
            source_type="structured_file",
        )
    if extension == "xlsx":
        sheets = _parse_xlsx_rows(file_bytes)
        return ParsedPayload(
            content_format="xlsx",
            payload_json=sheets,
            text_content=_structured_payload_text(sheets),
            source_type="structured_file",
        )
    if extension == "pdf":
        return _parse_pdf_file(file_bytes)
    raise ValueError(f"Unsupported extension for Phase 3 parser: {extension}")


def _decode_text(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def _xml_element_to_dict(element: ET.Element) -> dict[str, object]:
    children = list(element)
    node: dict[str, object] = {}
    if element.attrib:
        node["@attributes"] = dict(element.attrib)
    text = (element.text or "").strip()
    if text:
        node["@text"] = text
    for child in children:
        node.setdefault(child.tag, [])
        node[child.tag].append(_xml_element_to_dict(child))
    return node


def _parse_csv_rows(decoded_text: str) -> dict[str, object]:
    reader = csv.reader(StringIO(decoded_text))
    rows = [[_clean_cell_text(cell) for cell in row] for row in reader]
    if not rows:
        return {"headers": [], "rows": []}
    return _tabular_rows_to_payload(rows)


def _parse_xlsx_rows(file_bytes: bytes) -> dict[str, dict[str, object]]:
    with ZipFile(BytesIO(file_bytes)) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        namespace = {
            "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
        }
        relationship_map = {
            relationship.attrib["Id"]: relationship.attrib["Target"]
            for relationship in rels.findall("rel:Relationship", namespace)
        }
        sheets: dict[str, dict[str, object]] = {}
        for sheet in workbook.findall("main:sheets/main:sheet", namespace):
            name = sheet.attrib.get("name", "Sheet")
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = relationship_map.get(rel_id or "", "")
            sheet_path = f"xl/{target}" if not target.startswith("xl/") else target
            sheet_root = ET.fromstring(archive.read(sheet_path))
            rows: list[list[str | None]] = []
            for row in sheet_root.findall(".//main:sheetData/main:row", namespace):
                values: list[str | None] = []
                for cell in row.findall("main:c", namespace):
                    cell_type = cell.attrib.get("t")
                    value = cell.find("main:v", namespace)
                    inline_value = cell.find("main:is/main:t", namespace)
                    cell_text: str | None = None
                    if cell_type == "s" and value is not None and value.text is not None:
                        index = int(value.text)
                        cell_text = shared_strings[index] if 0 <= index < len(shared_strings) else value.text
                    elif inline_value is not None and inline_value.text is not None:
                        cell_text = inline_value.text
                    elif value is not None:
                        cell_text = value.text
                    values.append(cell_text)
                rows.append(values)
            sheets[name] = _tabular_rows_to_payload(rows)
        return sheets


def _xlsx_shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values: list[str] = []
    for item in root.findall("main:si", namespace):
        text_fragments = [node.text or "" for node in item.findall(".//main:t", namespace)]
        values.append("".join(text_fragments))
    return values


def _parse_pdf_file(file_bytes: bytes) -> ParsedPayload:
    fitz, _ = _pdf_runtime_modules()
    document = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[dict[str, object]] = []
    text_blocks: list[str] = []
    try:
        for page_index, page in enumerate(document, start=1):
            page_text = page.get_text("text")
            normalized_text = _normalize_extracted_text(page_text)
            pages.append(
                {
                    "page_number": page_index,
                    "text_length": len(normalized_text),
                    "has_text": bool(normalized_text),
                }
            )
            if normalized_text:
                text_blocks.append(f"[page:{page_index}]")
                text_blocks.append(normalized_text)
    finally:
        document.close()
    return ParsedPayload(
        content_format=PDF_CONTENT_FORMAT,
        payload_json={"page_count": len(pages), "pages": pages},
        text_content="\n".join(text_blocks),
        source_type="pdf",
    )


def _ocr_pdf_file(file_bytes: bytes) -> ParsedPayload:
    fitz, Image = _pdf_runtime_modules()
    import pytesseract

    document = fitz.open(stream=file_bytes, filetype="pdf")
    page_entries: list[dict[str, object]] = []
    text_blocks: list[str] = []
    try:
        for page_index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            ocr_text = pytesseract.image_to_string(image, lang="eng")
            normalized_text = _normalize_extracted_text(ocr_text)
            page_entries.append(
                {
                    "page_number": page_index,
                    "ocr_text_length": len(normalized_text),
                    "has_ocr_text": bool(normalized_text),
                }
            )
            if normalized_text:
                text_blocks.append(f"[page:{page_index}]")
                text_blocks.append(normalized_text)
    finally:
        document.close()
    return ParsedPayload(
        content_format=OCR_CONTENT_FORMAT,
        payload_json={"page_count": len(page_entries), "pages": page_entries},
        text_content="\n".join(text_blocks),
        source_type="ocr",
    )


def _fields_from_raw_extraction(raw_extraction: RawExtraction) -> list[tuple[str, str, str, str | None, int | None]]:
    fields: list[tuple[str, str, str, str | None, int | None]] = []
    if raw_extraction.payload_json is not None and raw_extraction.content_format in STRUCTURED_CONTENT_FORMATS:
        fields.extend(_flatten_structured_payload(raw_extraction.payload_json))
    if raw_extraction.text_content and raw_extraction.content_format not in STRUCTURED_CONTENT_FORMATS:
        current_page: int | None = None
        for line_number, line in enumerate(raw_extraction.text_content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            marker_match = PAGE_MARKER_PATTERN.match(stripped)
            if marker_match is not None:
                current_page = int(marker_match.group(1))
                continue
            locator_prefix = f"page:{current_page}:" if current_page is not None else ""
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                fields.append(
                    (_canonicalize_field_name(key), value.strip(), "text", f"{locator_prefix}line:{line_number}", current_page)
                )
            elif "=" in stripped:
                key, value = stripped.split("=", 1)
                fields.append(
                    (_canonicalize_field_name(key), value.strip(), "text", f"{locator_prefix}line:{line_number}", current_page)
                )
            else:
                fields.append((f"text_line_{line_number}", stripped, "text", f"{locator_prefix}line:{line_number}", current_page))
    deduped: list[tuple[str, str, str, str | None, int | None]] = []
    seen: set[tuple[str, str, str, str | None, int | None]] = set()
    for field in fields:
        if field in seen:
            continue
        seen.add(field)
        deduped.append(field)
    return deduped


def _flatten_structured_payload(payload: object, prefix: str = "") -> list[tuple[str, str, str, str | None, int | None]]:
    if isinstance(payload, dict):
        row_fields = _flatten_table_payload(payload, prefix)
        if row_fields:
            return row_fields
    return _flatten_payload(payload, prefix)


def _flatten_payload(payload: object, prefix: str = "") -> list[tuple[str, str, str, str | None, int | None]]:
    fields: list[tuple[str, str, str, str | None, int | None]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            fields.extend(_flatten_structured_payload(value, child_prefix))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            child_prefix = f"{prefix}[{index}]"
            fields.extend(_flatten_structured_payload(value, child_prefix))
    elif payload is not None:
        value_type = type(payload).__name__
        canonical_name = _canonicalize_field_name(prefix or "value")
        fields.append((canonical_name, str(payload), value_type, prefix or None, None))
    return fields


def _flatten_table_payload(payload: dict[str, object], prefix: str = "") -> list[tuple[str, str, str, str | None, int | None]]:
    rows = payload.get("rows")
    headers = payload.get("headers")
    if not isinstance(rows, list) or not isinstance(headers, list):
        return []

    fields: list[tuple[str, str, str, str | None, int | None]] = []
    table_prefix = prefix or "table"
    for row_index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            if key.startswith("_") or value in (None, ""):
                continue
            canonical_name = _canonicalize_field_name(key)
            value_type = type(value).__name__
            locator = f"{table_prefix}.row:{row_index}.column:{canonical_name}"
            fields.append((canonical_name, str(value), value_type, locator, None))
    return fields


def _tabular_rows_to_payload(rows: list[list[str | None]]) -> dict[str, object]:
    normalized_rows = [_trim_row(row) for row in rows if any(cell not in (None, "") for cell in row)]
    if not normalized_rows:
        return {"headers": [], "rows": []}

    header_index = _detect_header_row_index(normalized_rows)
    if header_index is None:
        return {
            "headers": [],
            "rows": [
                {"value": " | ".join(cell for cell in row if cell)}
                for row in normalized_rows
            ],
        }

    headers = [_normalize_header_cell(cell, position) for position, cell in enumerate(normalized_rows[header_index], start=1)]
    data_rows: list[dict[str, str]] = []
    for row in normalized_rows[header_index + 1 :]:
        row_dict: dict[str, str] = {}
        for position, header in enumerate(headers):
            if not header:
                continue
            cell = row[position] if position < len(row) else None
            cleaned = _clean_cell_text(cell)
            if cleaned:
                row_dict[header] = cleaned
        if row_dict:
            data_rows.append(row_dict)

    if data_rows:
        return {"headers": headers, "rows": data_rows}

    return {
        "headers": [],
        "rows": [
            {"value": " | ".join(cell for cell in row if cell)}
            for row in normalized_rows
        ],
    }


def _detect_header_row_index(rows: list[list[str | None]]) -> int | None:
    for index, row in enumerate(rows[:5]):
        populated = [cell for cell in row if cell not in (None, "")]
        if len(populated) < 2:
            continue
        if any(_looks_like_header_cell(cell or "") for cell in populated):
            return index
    return None


def _looks_like_header_cell(value: str) -> bool:
    cleaned = _clean_cell_text(value)
    if not cleaned:
        return False
    if _parse_amount(cleaned) is not None or _parse_date(cleaned) is not None:
        return False
    alpha_count = sum(character.isalpha() for character in cleaned)
    return alpha_count >= max(2, len(cleaned) // 3)


def _normalize_header_cell(value: str | None, position: int) -> str:
    cleaned = _clean_cell_text(value)
    if not cleaned:
        return f"column_{position}"
    return _canonicalize_field_name(cleaned)


def _trim_row(row: list[str | None]) -> list[str | None]:
    trimmed = list(row)
    while trimmed and trimmed[-1] in (None, ""):
        trimmed.pop()
    return [_clean_cell_text(cell) for cell in trimmed]


def _clean_cell_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _structured_payload_text(payload: object) -> str:
    lines: list[str] = []

    def walk(node: object, prefix: str = "") -> None:
        if isinstance(node, dict):
            row_payload = _flatten_table_payload(node, prefix)
            if row_payload:
                current_prefix = prefix or "table"
                lines.append(f"[table:{current_prefix}]")
                headers = node.get("headers")
                if isinstance(headers, list) and headers:
                    lines.append(f"{current_prefix}.headers={', '.join(str(header) for header in headers if header)}")
                for field_name, field_value, _, locator, _ in row_payload:
                    lines.append(f"{locator or current_prefix}:{field_name}={field_value}")
                return
            for key, value in node.items():
                child_prefix = f"{prefix}.{key}" if prefix else str(key)
                walk(value, child_prefix)
            return
        if isinstance(node, list):
            for index, value in enumerate(node):
                child_prefix = f"{prefix}[{index}]" if prefix else f"row[{index}]"
                walk(value, child_prefix)
            return
        if node not in (None, ""):
            lines.append(f"{prefix or 'value'}={node}")

    walk(payload)
    return "\n".join(line for line in lines if line.strip())


def _confidence_for_source(content_format: str) -> Decimal:
    if content_format in {"json", "xml", "csv", "xlsx"}:
        return Decimal("0.9000")
    if content_format == PDF_CONTENT_FORMAT:
        return Decimal("0.8000")
    if content_format == OCR_CONTENT_FORMAT:
        return Decimal("0.7000")
    return Decimal("0.5000")


def _extract_currency_code(value: str) -> str | None:
    match = CURRENCY_PATTERN.search(value)
    if match is None:
        return None
    return match.group(1).upper()


def _parse_date(value: str) -> date | None:
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value: str) -> Decimal | None:
    match = AMOUNT_PATTERN.search(value.replace("INR", "").replace("USD", "").replace(",", ""))
    if match is None:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def _normalized_item_for_field(field: ParsedField, document_type: str | None) -> dict[str, object] | None:
    field_name = field.field_name.lower()
    value = field.field_value_text
    amount = _parse_amount(value)
    category: NormalizedTaxItemCategory | None = None
    subcategory: str | None = None
    description = field.field_name
    document_hints = _document_category_hints(document_type)

    if field_name in {"gross_salary", "basic_salary", "salary_income"} and amount is not None:
        category = NormalizedTaxItemCategory.salary_income
        subcategory = "salary"
    elif field_name == "interest_income" and amount is not None:
        category = NormalizedTaxItemCategory.interest_income
        subcategory = "interest"
    elif "dividend" in field_name and amount is not None:
        is_foreign = "foreign" in field_name or (field.currency_code not in (None, "INR"))
        category = (
            NormalizedTaxItemCategory.foreign_dividend_income
            if is_foreign
            else NormalizedTaxItemCategory.domestic_dividend_income
        )
        subcategory = "dividend"
    elif field_name in {"short_term_capital_gain", "long_term_capital_gain", "capital_gains_total"} and amount is not None:
        category = NormalizedTaxItemCategory.capital_gains
        subcategory = field_name
    elif any(keyword in field_name for keyword in ("rsu", "esop", "vesting", "capital_gain", "capital_gains")) and amount is not None:
        category = NormalizedTaxItemCategory.capital_gains
        subcategory = "equity_event"
    elif field_name in {"tax_deducted", "tax_collected"} and amount is not None:
        category = NormalizedTaxItemCategory.tds_credits
        subcategory = "tds"
    elif "advance_tax" in field_name and amount is not None:
        category = NormalizedTaxItemCategory.advance_tax
        subcategory = "advance_tax"
    elif "self_assessment" in field_name and amount is not None:
        category = NormalizedTaxItemCategory.self_assessment_tax
        subcategory = "self_assessment_tax"
    elif any(keyword in field_name for keyword in ("deduction", "80c", "80d", "elss", "ppf", "donation")) and amount is not None:
        category = NormalizedTaxItemCategory.deductions
        subcategory = "deduction"
    elif amount is not None and document_type in {
        "insurance_premium_proof",
        "ppf_elss_proof",
        "donation_receipt",
        "tuition_fee_receipt",
        "medical_insurance_document",
        "rent_receipt",
        "home_loan_certificate",
    } and field_name in {
        "investment_amount",
        "premium_paid",
        "donation_amount",
        "tuition_fee_amount",
        "rent_paid",
        "home_loan_interest",
    }:
        category = NormalizedTaxItemCategory.deductions
        subcategory = field_name
    elif "withholding" in field_name and amount is not None:
        category = (
            NormalizedTaxItemCategory.tds_credits
            if document_type in {"form16", "form26as", "ais"}
            else NormalizedTaxItemCategory.other_sources
        )
        subcategory = "foreign_reference"
    elif amount is not None and field_name in {"income_paid"} and NormalizedTaxItemCategory.interest_income in document_hints:
        category = NormalizedTaxItemCategory.interest_income
        subcategory = "interest"
    elif amount is not None and field_name in {"income_paid"} and NormalizedTaxItemCategory.salary_income in document_hints:
        category = NormalizedTaxItemCategory.salary_income
        subcategory = "salary"
    elif amount is not None and field_name in {"income_paid"} and NormalizedTaxItemCategory.other_sources in document_hints:
        category = NormalizedTaxItemCategory.other_sources
        subcategory = "reported_income"
    elif amount is not None and field_name in {"sale_proceeds", "cost_basis"} and NormalizedTaxItemCategory.capital_gains in document_hints:
        category = NormalizedTaxItemCategory.capital_gains
        subcategory = field_name
    elif amount is not None and document_type in {"form16", "salary_slip"} and field_name in {"standard_deduction", "professional_tax"}:
        category = NormalizedTaxItemCategory.deductions
        subcategory = field_name
    elif amount is not None and document_type in {"ais", "form26as"} and field_name == "foreign_dividend_amount":
        category = NormalizedTaxItemCategory.foreign_dividend_income
        subcategory = "dividend"
    elif amount is not None and document_type in {"broker_statement", "capital_gains_statement"} and field_name in {"dividend_income"}:
        category = NormalizedTaxItemCategory.domestic_dividend_income
        subcategory = "dividend"

    if category is None:
        return None

    amount_in_inr = amount if field.currency_code in (None, "INR") else None
    return {
        "category": category,
        "subcategory": subcategory,
        "description": description,
        "amount": amount,
        "currency_code": field.currency_code,
        "amount_in_inr": amount_in_inr,
    }


def _foreign_income_event_for_item(
    document: Document,
    document_version_id: str,
    normalized: NormalizedTaxItem,
    field: ParsedField,
    field_map: dict[str, ParsedField],
) -> ForeignIncomeEvent | None:
    field_name = field.field_name.lower()
    if (
        normalized.category != NormalizedTaxItemCategory.foreign_dividend_income
        and "foreign" not in field_name
        and "rsu" not in field_name
        and "esop" not in field_name
        and "broker" not in field_name
        and "withholding" not in field_name
    ):
        return None

    event_type = "foreign_income_event"
    if "dividend" in field_name:
        event_type = "foreign_dividend"
    elif "rsu" in field_name or "vesting" in field_name:
        event_type = "rsu_vesting"
    elif "esop" in field_name:
        event_type = "esop_event"
    elif "broker" in field_name:
        event_type = "broker_statement"

    return ForeignIncomeEvent(
        id=str(uuid4()),
        document_id=document.id,
        document_version_id=document_version_id,
        normalized_tax_item_id=normalized.id,
        event_type=event_type,
        source_currency=field.currency_code,
        source_amount=_parse_amount(field.field_value_text),
        withholding_amount=_field_amount_like(field_map, "withholding"),
        broker_platform=_field_value_like(field_map, "broker"),
        country=_field_value_like(field_map, "country"),
        security_identifier=_field_value_like(field_map, "security"),
        event_date=field.event_date,
    )


def _field_value_like(field_map: dict[str, ParsedField], fragment: str) -> str | None:
    for name, field in field_map.items():
        if fragment in name:
            return field.field_value_text
    return None


def _field_amount_like(field_map: dict[str, ParsedField], fragment: str) -> Decimal | None:
    value = _field_value_like(field_map, fragment)
    if value is None:
        return None
    return _parse_amount(value)


def _record_validation_result(
    db: Session,
    document: Document,
    version: DocumentVersion,
    processing_job_id: str,
    text_probe: str,
    validation_state: DocumentValidationState,
    completeness_state: DocumentCompletenessState,
    plain_language_reason: str,
    is_relevant: bool,
    parseable: bool,
    duplicate_detected: bool,
    year_matches_filing: bool | None = None,
    detected_tax_year_label: str | None = None,
) -> None:
    del text_probe
    db.add(
        DocumentValidationResult(
            id=str(uuid4()),
            document_id=document.id,
            document_version_id=version.id,
            processing_job_id=processing_job_id,
            validation_state=validation_state,
            completeness_state=completeness_state,
            is_relevant=is_relevant,
            year_matches_filing=year_matches_filing,
            parseable=parseable,
            duplicate_detected=duplicate_detected,
            conflict_detected=False,
            detected_tax_year_label=detected_tax_year_label,
            plain_language_reason=plain_language_reason,
        )
    )


def _pdf_runtime_modules():
    import fitz
    from PIL import Image

    return fitz, Image


def _normalize_extracted_text(text: str | None) -> str:
    if text is None:
        return ""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _parsed_payload_has_meaningful_text(parsed: ParsedPayload) -> bool:
    return bool(_normalize_extracted_text(parsed.text_content))


def _ocr_job_exists(db: Session, document_id: str, document_version_id: str) -> bool:
    existing = db.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.document_id == document_id,
            ProcessingJob.document_version_id == document_version_id,
            ProcessingJob.job_type == ProcessingJobType.run_ocr,
        )
    )
    return existing is not None
