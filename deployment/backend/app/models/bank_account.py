from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    __table_args__ = {"schema": "app"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filing_id: Mapped[str] = mapped_column(String(36), ForeignKey("app.filings.id", ondelete="CASCADE"), nullable=False)
    account_holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number_masked: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ifsc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_primary_refund_account: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    filing: Mapped["Filing"] = relationship(back_populates="bank_accounts")


from app.models.filing import Filing  # noqa: E402

