"""Add description column to items

Revision ID: 005
Revises: 004
Create Date: 2026-05-29
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE items ADD COLUMN description TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE items DROP COLUMN IF EXISTS description")
