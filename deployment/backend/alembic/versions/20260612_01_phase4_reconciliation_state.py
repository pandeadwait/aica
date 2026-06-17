"""Add reconciliation state to review items

Revision ID: 20260612_01
Revises: 20260609_02
Create Date: 2026-06-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260612_01"
down_revision = "20260609_02"
branch_labels = None
depends_on = None


reconciliation_status_enum = sa.Enum(
    "unverified",
    "supported",
    "conflicted",
    "unsupported",
    name="reconciliation_status",
    schema="app",
)


def upgrade() -> None:
    reconciliation_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "category_assignments",
        sa.Column(
            "reconciliation_status",
            reconciliation_status_enum,
            nullable=False,
            server_default="unverified",
        ),
        schema="app",
    )
    op.add_column(
        "category_assignments",
        sa.Column("reconciliation_context_json", sa.JSON(), nullable=True),
        schema="app",
    )
    op.alter_column(
        "category_assignments",
        "reconciliation_status",
        server_default=None,
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("category_assignments", "reconciliation_context_json", schema="app")
    op.drop_column("category_assignments", "reconciliation_status", schema="app")
    op.execute("DROP TYPE IF EXISTS app.reconciliation_status")
