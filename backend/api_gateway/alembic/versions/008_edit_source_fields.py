"""add mime_type and raw_minio_key to document_edits

Revision ID: 008
Revises: 007
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_edits
            ADD COLUMN IF NOT EXISTS mime_type TEXT,
            ADD COLUMN IF NOT EXISTS raw_minio_key TEXT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_edits
            DROP COLUMN IF EXISTS mime_type,
            DROP COLUMN IF EXISTS raw_minio_key;
        """
    )
