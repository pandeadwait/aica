from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FilingStatus(str, enum.Enum):
    draft = "draft"
    collecting_documents = "collecting_documents"
    awaiting_user_clarification = "awaiting_user_clarification"
    ready_for_calculation = "ready_for_calculation"
    calculation_reviewed = "calculation_reviewed"
    xml_generated = "xml_generated"
    submitted_done = "submitted_done"
    archived = "archived"


class Filing(Base):
    __tablename__ = "filings"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assessment_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    financial_year_start: Mapped[int] = mapped_column(Integer, nullable=False)
    financial_year_end: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[FilingStatus] = mapped_column(
        Enum(FilingStatus, name="filing_status", schema="app"),
        nullable=False,
        default=FilingStatus.draft,
        index=True,
    )
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_filing_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("app.filings.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    taxpayer_profile: Mapped["TaxpayerProfile | None"] = relationship(back_populates="filing", uselist=False)
    bank_accounts: Mapped[list["BankAccount"]] = relationship(back_populates="filing")
    residency_detail: Mapped["ResidencyDetail | None"] = relationship(back_populates="filing", uselist=False)
    status_history: Mapped[list["FilingStatusHistory"]] = relationship(back_populates="filing")
    documents: Mapped[list["Document"]] = relationship(back_populates="filing")
    category_assignments: Mapped[list["CategoryAssignment"]] = relationship(back_populates="filing")
    review_sessions: Mapped[list["ReviewSession"]] = relationship(back_populates="filing")
    gap_items: Mapped[list["GapItem"]] = relationship(back_populates="filing")


class FilingStatusHistory(Base):
    __tablename__ = "filing_status_history"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[FilingStatus | None] = mapped_column(
        Enum(FilingStatus, name="filing_status", schema="app"), nullable=True
    )
    to_status: Mapped[FilingStatus] = mapped_column(
        Enum(FilingStatus, name="filing_status", schema="app"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    filing: Mapped[Filing] = relationship(back_populates="status_history")


from app.models.bank_account import BankAccount  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.review import CategoryAssignment, GapItem, ReviewSession  # noqa: E402
from app.models.residency_detail import ResidencyDetail  # noqa: E402
from app.models.taxpayer_profile import TaxpayerProfile  # noqa: E402
