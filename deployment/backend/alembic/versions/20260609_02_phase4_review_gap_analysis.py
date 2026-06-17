"""Phase 4 review, categorization, and gap analysis schema

Revision ID: 20260609_02
Revises: 20260609_01
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260609_02"
down_revision = "20260609_01"
branch_labels = None
depends_on = None


review_item_status_enum = sa.Enum(
    "candidate",
    "accepted",
    "overridden",
    "split",
    "rejected",
    "marked_for_later",
    name="review_item_status",
    schema="app",
)

gap_severity_enum = sa.Enum(
    "critical",
    "warning",
    "info",
    name="gap_severity",
    schema="app",
)

gap_resolution_status_enum = sa.Enum(
    "open",
    "resolved",
    "dismissed",
    name="gap_resolution_status",
    schema="app",
)

normalized_tax_item_category_enum = postgresql.ENUM(
    "salary_income",
    "interest_income",
    "domestic_dividend_income",
    "foreign_dividend_income",
    "capital_gains",
    "deductions",
    "tds_credits",
    "advance_tax",
    "self_assessment_tax",
    "other_sources",
    name="normalized_tax_item_category",
    schema="app",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "category_assignments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False),
        sa.Column("normalized_tax_item_id", sa.String(length=36), nullable=True),
        sa.Column("source_parsed_field_id", sa.String(length=36), nullable=True),
        sa.Column("parent_assignment_id", sa.String(length=36), nullable=True),
        sa.Column("suggested_category", normalized_tax_item_category_enum, nullable=False),
        sa.Column("final_category", normalized_tax_item_category_enum, nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column("amount_in_inr", sa.Numeric(18, 2), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0.5000"),
        sa.Column("status", review_item_status_enum, nullable=False, server_default="candidate"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["normalized_tax_item_id"], ["app.normalized_tax_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_parsed_field_id"], ["app.parsed_fields.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_assignment_id"], ["app.category_assignments.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_category_assignments_filing_id", "category_assignments", ["filing_id"], schema="app")
    op.create_index("ix_category_assignments_normalized_tax_item_id", "category_assignments", ["normalized_tax_item_id"], schema="app")
    op.create_index("ix_category_assignments_parent_assignment_id", "category_assignments", ["parent_assignment_id"], schema="app")

    op.create_table(
        "manual_overrides",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("category_assignment_id", sa.String(length=36), nullable=False),
        sa.Column("override_type", sa.String(length=50), nullable=False),
        sa.Column("from_category", normalized_tax_item_category_enum, nullable=True),
        sa.Column("to_category", normalized_tax_item_category_enum, nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["category_assignment_id"], ["app.category_assignments.id"], ondelete="CASCADE"),
        schema="app",
    )
    op.create_index("ix_manual_overrides_category_assignment_id", "manual_overrides", ["category_assignment_id"], schema="app")

    op.create_table(
        "review_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        schema="app",
    )
    op.create_index("ix_review_sessions_filing_id", "review_sessions", ["filing_id"], schema="app")

    op.create_table(
        "gap_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False),
        sa.Column("gap_key", sa.String(length=255), nullable=False),
        sa.Column("gap_code", sa.String(length=100), nullable=False),
        sa.Column("severity", gap_severity_enum, nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("resolution_status", gap_resolution_status_enum, nullable=False, server_default="open"),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("filing_id", "gap_key", name="uq_gap_items_filing_key"),
        schema="app",
    )
    op.create_index("ix_gap_items_filing_id", "gap_items", ["filing_id"], schema="app")

    op.create_table(
        "gap_resolutions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("gap_item_id", sa.String(length=36), nullable=False),
        sa.Column("resolution_action", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["gap_item_id"], ["app.gap_items.id"], ondelete="CASCADE"),
        schema="app",
    )
    op.create_index("ix_gap_resolutions_gap_item_id", "gap_resolutions", ["gap_item_id"], schema="app")


def downgrade() -> None:
    op.drop_index("ix_gap_resolutions_gap_item_id", table_name="gap_resolutions", schema="app")
    op.drop_table("gap_resolutions", schema="app")
    op.drop_index("ix_gap_items_filing_id", table_name="gap_items", schema="app")
    op.drop_table("gap_items", schema="app")
    op.drop_index("ix_review_sessions_filing_id", table_name="review_sessions", schema="app")
    op.drop_table("review_sessions", schema="app")
    op.drop_index("ix_manual_overrides_category_assignment_id", table_name="manual_overrides", schema="app")
    op.drop_table("manual_overrides", schema="app")
    op.drop_index("ix_category_assignments_parent_assignment_id", table_name="category_assignments", schema="app")
    op.drop_index("ix_category_assignments_normalized_tax_item_id", table_name="category_assignments", schema="app")
    op.drop_index("ix_category_assignments_filing_id", table_name="category_assignments", schema="app")
    op.drop_table("category_assignments", schema="app")
    op.execute("DROP TYPE IF EXISTS app.gap_resolution_status")
    op.execute("DROP TYPE IF EXISTS app.gap_severity")
    op.execute("DROP TYPE IF EXISTS app.review_item_status")
