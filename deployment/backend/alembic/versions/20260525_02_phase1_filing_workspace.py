"""Phase 1 filing workspace schema

Revision ID: 20260525_02
Revises: 20260525_01
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260525_02"
down_revision = "20260525_01"
branch_labels = None
depends_on = None


filing_status_enum = sa.Enum(
    "draft",
    "collecting_documents",
    "awaiting_user_clarification",
    "ready_for_calculation",
    "calculation_reviewed",
    "xml_generated",
    "submitted_done",
    "archived",
    name="filing_status",
    schema="app",
)


def upgrade() -> None:
    op.create_table(
        "filings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("assessment_year", sa.Integer(), nullable=False),
        sa.Column("financial_year_start", sa.Integer(), nullable=False),
        sa.Column("financial_year_end", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", filing_status_enum, nullable=False, server_default="draft"),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_filing_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["source_filing_id"], ["app.filings.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_filings_assessment_year", "filings", ["assessment_year"], schema="app")
    op.create_index("ix_filings_status", "filings", ["status"], schema="app")

    op.create_table(
        "filing_status_history",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False),
        sa.Column("from_status", filing_status_enum, nullable=True),
        sa.Column("to_status", filing_status_enum, nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        schema="app",
    )
    op.create_index("ix_filing_status_history_filing_id", "filing_status_history", ["filing_id"], schema="app")

    op.create_table(
        "taxpayer_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("pan", sa.String(length=10), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("residential_status", sa.String(length=50), nullable=True),
        sa.Column("aadhaar_available", sa.Boolean(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("employer_name", sa.String(length=255), nullable=True),
        sa.Column("preferred_tax_regime", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        schema="app",
    )

    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False),
        sa.Column("account_holder_name", sa.String(length=255), nullable=True),
        sa.Column("bank_name", sa.String(length=255), nullable=True),
        sa.Column("account_number_masked", sa.String(length=32), nullable=True),
        sa.Column("ifsc_code", sa.String(length=20), nullable=True),
        sa.Column("is_primary_refund_account", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        schema="app",
    )
    op.create_index("ix_bank_accounts_filing_id", "bank_accounts", ["filing_id"], schema="app")

    op.create_table(
        "residency_details",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("country_of_residence", sa.String(length=100), nullable=True),
        sa.Column("days_in_india", sa.Integer(), nullable=True),
        sa.Column("has_foreign_assets", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("has_foreign_income", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("residency_details", schema="app")
    op.drop_index("ix_bank_accounts_filing_id", table_name="bank_accounts", schema="app")
    op.drop_table("bank_accounts", schema="app")
    op.drop_table("taxpayer_profiles", schema="app")
    op.drop_index("ix_filing_status_history_filing_id", table_name="filing_status_history", schema="app")
    op.drop_table("filing_status_history", schema="app")
    op.drop_index("ix_filings_status", table_name="filings", schema="app")
    op.drop_index("ix_filings_assessment_year", table_name="filings", schema="app")
    op.drop_table("filings", schema="app")
    op.execute("DROP TYPE IF EXISTS app.filing_status")
