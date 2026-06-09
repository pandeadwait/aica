from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaxpayerProfile(Base):
    __tablename__ = "taxpayer_profiles"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    residential_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    aadhaar_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    employer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_tax_regime: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship(back_populates="taxpayer_profile")


from app.models.filing import Filing  # noqa: E402

