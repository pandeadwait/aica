"""Phase 0 foundation schema

Revision ID: 20260525_01
Revises:
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op


revision = "20260525_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("CREATE SCHEMA IF NOT EXISTS retrieval")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS retrieval CASCADE")
    op.execute("DROP SCHEMA IF EXISTS app CASCADE")

