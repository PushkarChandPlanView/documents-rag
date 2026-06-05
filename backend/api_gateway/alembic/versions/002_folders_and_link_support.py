"""Add folders table and link/folder fields to documents

Revision ID: 002
Revises: 001
Create Date: 2026-05-28

"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # folders table
    op.execute("""
        CREATE TABLE folders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            parent_id UUID REFERENCES folders(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_folders_user_id ON folders (user_id)")
    op.execute("CREATE INDEX ix_folders_parent_id ON folders (parent_id)")

    # Add folder_id and source_url to documents
    op.execute("""
        ALTER TABLE documents
            ADD COLUMN folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
            ADD COLUMN source_url VARCHAR(2000)
    """)
    op.execute("CREATE INDEX ix_documents_folder_id ON documents (folder_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_documents_folder_id")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS folder_id, DROP COLUMN IF EXISTS source_url")
    op.execute("DROP TABLE IF EXISTS folders")
