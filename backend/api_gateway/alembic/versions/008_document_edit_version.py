"""Add version column to document_edits

Revision ID: 008
Revises: 007
Create Date: 2026-06-09
"""
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_edits ADD COLUMN IF NOT EXISTS version INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE document_edits DROP COLUMN IF EXISTS version")
