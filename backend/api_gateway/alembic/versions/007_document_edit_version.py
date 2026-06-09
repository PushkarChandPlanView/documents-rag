"""Add version column to document_edits

Revision ID: 007
Revises: 006
Create Date: 2026-06-09
"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_edits ADD COLUMN IF NOT EXISTS version INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE document_edits DROP COLUMN IF EXISTS version")
