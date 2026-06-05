"""Change items.parent_id FK to ON DELETE CASCADE

Revision ID: 004
Revises: 003
Create Date: 2026-05-29
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE items DROP CONSTRAINT items_parent_id_fkey")
    op.execute("""
        ALTER TABLE items
            ADD CONSTRAINT items_parent_id_fkey
            FOREIGN KEY (parent_id) REFERENCES items(id) ON DELETE CASCADE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE items DROP CONSTRAINT items_parent_id_fkey")
    op.execute("""
        ALTER TABLE items
            ADD CONSTRAINT items_parent_id_fkey
            FOREIGN KEY (parent_id) REFERENCES items(id) ON DELETE SET NULL
    """)
