"""Add source_type column to documents table

Revision ID: 006
Revises: 005
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source_type", sa.String(50), nullable=True),
    )
    op.create_index("ix_documents_source_type", "documents", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_documents_source_type", table_name="documents")
    op.drop_column("documents", "source_type")
