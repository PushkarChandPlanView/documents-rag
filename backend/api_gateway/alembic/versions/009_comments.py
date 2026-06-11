"""create comments and comment_likes tables

Revision ID: 009
Revises: 008
Create Date: 2025-01-01 00:00:00.000000

Design decisions:
- UUID primary keys for distributed-safe IDs.
- Soft-delete on comments (deleted_at) so replies are never orphaned.
- Partial index on comments(document_id) filters deleted rows at the DB level.
- UNIQUE constraint on (user_id, comment_id) in comment_likes enforces one-like-per-user.
- ON DELETE CASCADE on foreign keys keeps the DB consistent without app-layer cleanup.
"""
from alembic import op

revision = "009"
down_revision = "008b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID        NOT NULL
                            REFERENCES users(id)     ON DELETE CASCADE,
            document_id UUID        NOT NULL
                            REFERENCES documents(id) ON DELETE CASCADE,
            parent_id   UUID
                            REFERENCES comments(id)  ON DELETE CASCADE,
            content     TEXT        NOT NULL
                            CONSTRAINT ck_comment_content_length
                            CHECK (char_length(content) BETWEEN 1 AND 10000),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ
        );
        """
    )

    # Speed up "get all top-level comments for a document" (the hot read path)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_comments_document_id_active
            ON comments (document_id, created_at DESC)
            WHERE deleted_at IS NULL;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments (parent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_comments_user_id    ON comments (user_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS comment_likes (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
            comment_id  UUID        NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT  uq_comment_likes_user_comment UNIQUE (user_id, comment_id)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_comment_likes_comment_id ON comment_likes (comment_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS comment_likes;")
    op.execute("DROP TABLE IF EXISTS comments;")
