"""Add version column to document_edits

Revision ID: 008b
Revises: 008
Create Date: 2026-06-09
"""
from alembic import op

revision = "008b"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_edits ADD COLUMN IF NOT EXISTS version INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE document_edits DROP COLUMN IF EXISTS version")
