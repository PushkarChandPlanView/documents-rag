"""Add pgvector extension and document_embeddings table

Revision ID: 002
Revises: 001
Create Date: 2026-05-30

Note: The `vector` extension is pre-created in init.sql (requires superuser).
      The `CREATE EXTENSION IF NOT EXISTS` here is a safe no-op on clean deployments
      and a fallback for environments where init.sql wasn't run with superuser rights.
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op if init.sql already ran it; required fallback otherwise.
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    op.execute("""
        CREATE TABLE document_embeddings (
            chunk_id      UUID    PRIMARY KEY
                              REFERENCES document_chunks(id) ON DELETE CASCADE,
            document_id   UUID    NOT NULL
                              REFERENCES documents(id) ON DELETE CASCADE,
            user_id       UUID    NOT NULL,
            chunk_index   INTEGER NOT NULL,
            page_number   INTEGER,
            document_name TEXT    NOT NULL DEFAULT '',
            file_type     TEXT    NOT NULL DEFAULT '',
            char_count    INTEGER NOT NULL DEFAULT 0,
            token_count   INTEGER NOT NULL DEFAULT 0,
            total_chunks  INTEGER NOT NULL DEFAULT 0,
            embedding     vector(1024)
        )
    """)

    # IVFFlat cosine index.
    # Tune `lists` as corpus grows — rule of thumb: sqrt(total rows), min 100.
    op.execute("""
        CREATE INDEX document_embeddings_embedding_idx
            ON document_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
    """)

    op.execute("""
        CREATE INDEX document_embeddings_user_id_idx
            ON document_embeddings (user_id)
    """)

    op.execute("""
        CREATE INDEX document_embeddings_document_id_idx
            ON document_embeddings (document_id)
    """)

    op.execute("""
        CREATE INDEX document_embeddings_user_doc_idx
            ON document_embeddings (user_id, document_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_embeddings")
