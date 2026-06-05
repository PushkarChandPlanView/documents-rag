"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-29
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # users
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_users_email ON users (email)")

    # documents — single table for both folders and documents (type discriminator)
    op.execute("""
        CREATE TABLE documents (
            id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            type            VARCHAR(20)  NOT NULL CHECK (type IN ('folder', 'document')),
            user_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name            VARCHAR(500) NOT NULL,
            description     TEXT,
            parent_id       UUID         REFERENCES documents(id) ON DELETE CASCADE,
            mime_type       VARCHAR(200),
            file_size_bytes INTEGER,
            minio_key       VARCHAR(1000),
            source_url      VARCHAR(2000),
            status          VARCHAR(50),
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_documents_user_id   ON documents (user_id)")
    op.execute("CREATE INDEX ix_documents_type      ON documents (type)")
    op.execute("CREATE INDEX ix_documents_parent_id ON documents (parent_id)")
    op.execute("CREATE INDEX ix_documents_status    ON documents (status)")

    # document_chunks
    op.execute("""
        CREATE TABLE document_chunks (
            id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID    NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            text        TEXT    NOT NULL,
            char_count  INTEGER NOT NULL,
            page_number INTEGER,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id)")

    # document_summaries
    op.execute("""
        CREATE TABLE document_summaries (
            id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID    NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            summary     TEXT    NOT NULL,
            model       VARCHAR(200),
            strategy    VARCHAR(50),
            version     INTEGER NOT NULL DEFAULT 1,
            is_active   BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_document_summaries_document_id ON document_summaries (document_id)")
    op.execute("CREATE INDEX ix_document_summaries_is_active   ON document_summaries (is_active)")

    # processing_jobs
    op.execute("""
        CREATE TABLE processing_jobs (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id   UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            stage         VARCHAR(50) NOT NULL,
            status        VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            error_message TEXT,
            started_at    TIMESTAMPTZ,
            completed_at  TIMESTAMPTZ,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_processing_jobs_document_id ON processing_jobs (document_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS processing_jobs")
    op.execute("DROP TABLE IF EXISTS document_summaries")
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS users")
