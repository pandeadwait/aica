from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResidencyDetail(Base):
    __tablename__ = "residency_details"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    country_of_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    days_in_india: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_foreign_assets: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_foreign_income: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship(back_populates="residency_detail")


from app.models.filing import Filing  # noqa: E402

