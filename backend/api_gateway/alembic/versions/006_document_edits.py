"""Add document_edits table for chat-driven document editing

Revision ID: 006
Revises: 005
Create Date: 2026-06-09
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE document_edits (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id      UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            user_id          UUID        NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
            instruction      TEXT        NOT NULL,
            original_content TEXT        NOT NULL,
            proposed_content TEXT        NOT NULL,
            status           VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_document_edits_document_id ON document_edits (document_id)")
    op.execute("CREATE INDEX ix_document_edits_user_id     ON document_edits (user_id)")
    op.execute("CREATE INDEX ix_document_edits_status      ON document_edits (status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_edits")
