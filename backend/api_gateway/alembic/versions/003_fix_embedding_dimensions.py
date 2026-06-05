"""Change document_embeddings.embedding from vector(768) to vector(1024)

Revision ID: 003
Revises: 002
Create Date: 2026-05-30

mxbai-embed-large produces 1024-dimensional vectors, not 768.
This migration alters the column and recreates the IVFFlat index.
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old index first (can't alter a vector column with an index on it)
    op.execute("DROP INDEX IF EXISTS document_embeddings_embedding_idx")

    # Alter the column — pgvector allows ALTER COLUMN ... TYPE vector(N)
    op.execute("""
        ALTER TABLE document_embeddings
            ALTER COLUMN embedding TYPE vector(1024)
    """)

    # Recreate the IVFFlat cosine index for 1024-dim vectors
    op.execute("""
        CREATE INDEX document_embeddings_embedding_idx
            ON document_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS document_embeddings_embedding_idx")
    op.execute("""
        ALTER TABLE document_embeddings
            ALTER COLUMN embedding TYPE vector(768)
    """)
    op.execute("""
        CREATE INDEX document_embeddings_embedding_idx
            ON document_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
    """)
