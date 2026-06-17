from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.processing import NormalizedTaxItemCategory

if TYPE_CHECKING:
    from app.models.filing import Filing
    from app.models.processing import NormalizedTaxItem, ParsedField


class ReviewItemStatus(str, enum.Enum):
    candidate = "candidate"
    accepted = "accepted"
    overridden = "overridden"
    split = "split"
    rejected = "rejected"
    marked_for_later = "marked_for_later"


class ReconciliationStatus(str, enum.Enum):
    unverified = "unverified"
    supported = "supported"
    conflicted = "conflicted"
    unsupported = "unsupported"


class GapSeverity(str, enum.Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class GapResolutionStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class CategoryAssignment(Base):
    __tablename__ = "category_assignments"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), index=True)
    normalized_tax_item_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.normalized_tax_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_parsed_field_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.parsed_fields.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_assignment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("app.category_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    suggested_category: Mapped[NormalizedTaxItemCategory] = mapped_column(
        Enum("salary_income", "interest_income", "domestic_dividend_income", "foreign_dividend_income", "capital_gains", "deductions", "tds_credits", "advance_tax", "self_assessment_tax", "other_sources", name="normalized_tax_item_category", schema="app"),
        nullable=False,
    )
    final_category: Mapped[NormalizedTaxItemCategory | None] = mapped_column(
        Enum("salary_income", "interest_income", "domestic_dividend_income", "foreign_dividend_income", "capital_gains", "deductions", "tds_credits", "advance_tax", "self_assessment_tax", "other_sources", name="normalized_tax_item_category", schema="app"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    amount_in_inr: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0.5000"))
    status: Mapped[ReviewItemStatus] = mapped_column(
        Enum(ReviewItemStatus, name="review_item_status", schema="app"),
        nullable=False,
        default=ReviewItemStatus.candidate,
    )
    reconciliation_status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus, name="reconciliation_status", schema="app"),
        nullable=False,
        default=ReconciliationStatus.unverified,
    )
    reconciliation_context_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship(back_populates="category_assignments")
    normalized_tax_item: Mapped["NormalizedTaxItem | None"] = relationship(back_populates="category_assignments")
    source_parsed_field: Mapped["ParsedField | None"] = relationship()
    parent_assignment: Mapped["CategoryAssignment | None"] = relationship(remote_side="CategoryAssignment.id")
    manual_overrides: Mapped[list["ManualOverride"]] = relationship(
        back_populates="category_assignment",
        cascade="all, delete-orphan",
    )


class ManualOverride(Base):
    __tablename__ = "manual_overrides"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_assignment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.category_assignments.id", ondelete="CASCADE"),
        index=True,
    )
    override_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_category: Mapped[NormalizedTaxItemCategory | None] = mapped_column(
        Enum("salary_income", "interest_income", "domestic_dividend_income", "foreign_dividend_income", "capital_gains", "deductions", "tds_credits", "advance_tax", "self_assessment_tax", "other_sources", name="normalized_tax_item_category", schema="app"),
        nullable=True,
    )
    to_category: Mapped[NormalizedTaxItemCategory | None] = mapped_column(
        Enum("salary_income", "interest_income", "domestic_dividend_income", "foreign_dividend_income", "capital_gains", "deductions", "tds_credits", "advance_tax", "self_assessment_tax", "other_sources", name="normalized_tax_item_category", schema="app"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    category_assignment: Mapped[CategoryAssignment] = relationship(back_populates="manual_overrides")


class ReviewSession(Base):
    __tablename__ = "review_sessions"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    filing: Mapped["Filing"] = relationship(back_populates="review_sessions")


class GapItem(Base):
    __tablename__ = "gap_items"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), index=True)
    gap_key: Mapped[str] = mapped_column(String(255), nullable=False)
    gap_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[GapSeverity] = mapped_column(
        Enum(GapSeverity, name="gap_severity", schema="app"),
        nullable=False,
    )
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_status: Mapped[GapResolutionStatus] = mapped_column(
        Enum(GapResolutionStatus, name="gap_resolution_status", schema="app"),
        nullable=False,
        default=GapResolutionStatus.open,
    )
    context_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship(back_populates="gap_items")
    resolutions: Mapped[list["GapResolution"]] = relationship(
        back_populates="gap_item",
        cascade="all, delete-orphan",
    )


class GapResolution(Base):
    __tablename__ = "gap_resolutions"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    gap_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app.gap_items.id", ondelete="CASCADE"),
        index=True,
    )
    resolution_action: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    gap_item: Mapped[GapItem] = relationship(back_populates="resolutions")
