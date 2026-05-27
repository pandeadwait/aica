"""Phase 2 document intake schema

Revision ID: 20260526_01
Revises: 20260525_02
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_01"
down_revision = "20260525_02"
branch_labels = None
depends_on = None


document_processing_status_enum = sa.Enum(
    "uploaded",
    "duplicate",
    "queued",
    "processing",
    "completed",
    "failed",
    "needs_review",
    name="document_processing_status",
    schema="app",
)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filing_id", sa.String(length=36), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column(
            "processing_status",
            document_processing_status_enum,
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["filing_id"], ["app.filings.id"], ondelete="CASCADE"),
        schema="app",
    )
    op.create_index("ix_documents_filing_id", "documents", ["filing_id"], schema="app")
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"], schema="app")

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_doc_version"),
        schema="app",
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"], schema="app")
    op.create_index("ix_document_versions_checksum", "document_versions", ["checksum_sha256"], schema="app")

    op.create_table(
        "document_storage_refs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_version_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="CASCADE"),
        schema="app",
    )

    op.create_table(
        "document_upload_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["app.documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["app.document_versions.id"], ondelete="SET NULL"),
        schema="app",
    )
    op.create_index("ix_document_upload_events_document_id", "document_upload_events", ["document_id"], schema="app")


def downgrade() -> None:
    op.drop_index("ix_document_upload_events_document_id", table_name="document_upload_events", schema="app")
    op.drop_table("document_upload_events", schema="app")
    op.drop_table("document_storage_refs", schema="app")
    op.drop_index("ix_document_versions_checksum", table_name="document_versions", schema="app")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions", schema="app")
    op.drop_table("document_versions", schema="app")
    op.drop_index("ix_documents_processing_status", table_name="documents", schema="app")
    op.drop_index("ix_documents_filing_id", table_name="documents", schema="app")
    op.drop_table("documents", schema="app")
    op.execute("DROP TYPE IF EXISTS app.document_processing_status")
