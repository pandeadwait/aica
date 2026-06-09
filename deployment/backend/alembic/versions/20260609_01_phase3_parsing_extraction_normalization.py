"""Phase 3 parsing, extraction, and normalization schema

Revision ID: 20260609_01
Revises: 20260526_01
Create Date: 2026-06-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260609_01"
down_revision = "20260526_01"
branch_labels = None
depends_on = None


processing_job_type_enum = sa.Enum(
    "validate_document",
    "parse_document",
    "run_ocr",
    "extract_fields",
    "normalize_tax_items",
    name="processing_job_type",
    schema="app",
)

processing_job_status_enum = sa.Enum(
    "pending",
    "processing",
    "completed",
    "failed",
    "needs_review",
    name="processing_job_status",
    schema="app",
)

document_validation_state_enum = sa.Enum(
    "relevant",
    "possibly_relevant",
    "not_relevant",
    "unsupported",
    "duplicate",
    "corrupted_unreadable",
    "needs_user_review",
    name="document_validation_state",
    schema="app",
)

document_completeness_state_enum = sa.Enum(
    "complete",
    "partial",
    "incomplete",
    "unknown",
    name="document_completeness_state",
    schema="app",
)

normalized_tax_item_category_enum = sa.Enum(
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
)


def upgrade() -> None:
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("job_type", processing_job_type_enum, nullable=False),
        sa.Column("status", processing_job_status_enum, nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="CASCADE"),
        schema="app",
    )
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"], schema="app")
    op.create_index("ix_processing_jobs_document_version_id", "processing_jobs", ["document_version_id"], schema="app")
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"], schema="app")

    op.create_table(
        "document_validation_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("processing_job_id", sa.String(length=36), nullable=True),
        sa.Column("validation_state", document_validation_state_enum, nullable=False),
        sa.Column("completeness_state", document_completeness_state_enum, nullable=False, server_default="unknown"),
        sa.Column("is_relevant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("year_matches_filing", sa.Boolean(), nullable=True),
        sa.Column("parseable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("duplicate_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("conflict_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("detected_tax_year_label", sa.String(length=50), nullable=True),
        sa.Column("plain_language_reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["app.processing_jobs.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index(
        "ix_document_validation_results_document_id",
        "document_validation_results",
        ["document_id"],
        schema="app",
    )
    op.create_index(
        "ix_document_validation_results_document_version_id",
        "document_validation_results",
        ["document_version_id"],
        schema="app",
    )

    op.create_table(
        "raw_extractions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("processing_job_id", sa.String(length=36), nullable=True),
        sa.Column("extraction_stage", sa.String(length=50), nullable=False),
        sa.Column("content_format", sa.String(length=50), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["app.processing_jobs.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_raw_extractions_document_id", "raw_extractions", ["document_id"], schema="app")
    op.create_index(
        "ix_raw_extractions_document_version_id",
        "raw_extractions",
        ["document_version_id"],
        schema="app",
    )

    op.create_table(
        "parsed_fields",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("raw_extraction_id", sa.String(length=36), nullable=True),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("field_value_text", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0.5000"),
        sa.Column("source_locator", sa.String(length=255), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_extraction_id"], ["app.raw_extractions.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_parsed_fields_document_id", "parsed_fields", ["document_id"], schema="app")
    op.create_index("ix_parsed_fields_document_version_id", "parsed_fields", ["document_version_id"], schema="app")

    op.create_table(
        "field_provenance",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("parsed_field_id", sa.String(length=36), nullable=False),
        sa.Column("raw_extraction_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_locator", sa.String(length=255), nullable=True),
        sa.Column("source_snippet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["parsed_field_id"], ["app.parsed_fields.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_extraction_id"], ["app.raw_extractions.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_field_provenance_parsed_field_id", "field_provenance", ["parsed_field_id"], schema="app")

    op.create_table(
        "normalized_tax_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("processing_job_id", sa.String(length=36), nullable=True),
        sa.Column("source_parsed_field_id", sa.String(length=36), nullable=True),
        sa.Column("category", normalized_tax_item_category_enum, nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency_code", sa.String(length=10), nullable=True),
        sa.Column("amount_in_inr", sa.Numeric(18, 2), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0.5000"),
        sa.Column("review_status", sa.String(length=50), nullable=False, server_default="candidate"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["app.processing_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_parsed_field_id"], ["app.parsed_fields.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_normalized_tax_items_document_id", "normalized_tax_items", ["document_id"], schema="app")
    op.create_index(
        "ix_normalized_tax_items_document_version_id",
        "normalized_tax_items",
        ["document_version_id"],
        schema="app",
    )

    op.create_table(
        "foreign_income_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("normalized_tax_item_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source_currency", sa.String(length=10), nullable=True),
        sa.Column("source_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("withholding_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("broker_platform", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("security_identifier", sa.String(length=100), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["normalized_tax_item_id"], ["app.normalized_tax_items.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_foreign_income_events_document_id", "foreign_income_events", ["document_id"], schema="app")
    op.create_index(
        "ix_foreign_income_events_document_version_id",
        "foreign_income_events",
        ["document_version_id"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_index("ix_foreign_income_events_document_version_id", table_name="foreign_income_events", schema="app")
    op.drop_index("ix_foreign_income_events_document_id", table_name="foreign_income_events", schema="app")
    op.drop_table("foreign_income_events", schema="app")
    op.drop_index("ix_normalized_tax_items_document_version_id", table_name="normalized_tax_items", schema="app")
    op.drop_index("ix_normalized_tax_items_document_id", table_name="normalized_tax_items", schema="app")
    op.drop_table("normalized_tax_items", schema="app")
    op.drop_index("ix_field_provenance_parsed_field_id", table_name="field_provenance", schema="app")
    op.drop_table("field_provenance", schema="app")
    op.drop_index("ix_parsed_fields_document_version_id", table_name="parsed_fields", schema="app")
    op.drop_index("ix_parsed_fields_document_id", table_name="parsed_fields", schema="app")
    op.drop_table("parsed_fields", schema="app")
    op.drop_index("ix_raw_extractions_document_version_id", table_name="raw_extractions", schema="app")
    op.drop_index("ix_raw_extractions_document_id", table_name="raw_extractions", schema="app")
    op.drop_table("raw_extractions", schema="app")
    op.drop_index(
        "ix_document_validation_results_document_version_id",
        table_name="document_validation_results",
        schema="app",
    )
    op.drop_index(
        "ix_document_validation_results_document_id",
        table_name="document_validation_results",
        schema="app",
    )
    op.drop_table("document_validation_results", schema="app")
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs", schema="app")
    op.drop_index("ix_processing_jobs_document_version_id", table_name="processing_jobs", schema="app")
    op.drop_index("ix_processing_jobs_document_id", table_name="processing_jobs", schema="app")
    op.drop_table("processing_jobs", schema="app")
    op.execute("DROP TYPE IF EXISTS app.normalized_tax_item_category")
    op.execute("DROP TYPE IF EXISTS app.document_completeness_state")
    op.execute("DROP TYPE IF EXISTS app.document_validation_state")
    op.execute("DROP TYPE IF EXISTS app.processing_job_status")
    op.execute("DROP TYPE IF EXISTS app.processing_job_type")
