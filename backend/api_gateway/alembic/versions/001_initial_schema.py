"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # Enums
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE document_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE processing_stage AS ENUM ('TEXT_EXTRACTION', 'CHUNKING', 'EMBEDDING', 'SUMMARIZATION');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE job_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # users
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_users_email UNIQUE (email)
        )
    """)
    op.execute("CREATE INDEX ix_users_email ON users (email)")

    # documents
    op.execute("""
        CREATE TABLE documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename VARCHAR(500) NOT NULL,
            minio_key VARCHAR(1000) NOT NULL DEFAULT '',
            mime_type VARCHAR(200) NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            status document_status NOT NULL DEFAULT 'PENDING',
            summary TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_documents_user_id ON documents (user_id)")
    op.execute("CREATE INDEX ix_documents_status ON documents (status)")

    # document_chunks
    op.execute("""
        CREATE TABLE document_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            page_number INTEGER,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id)")

    # processing_jobs
    op.execute("""
        CREATE TABLE processing_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            stage processing_stage NOT NULL,
            status job_status NOT NULL DEFAULT 'PENDING',
            error_message TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_processing_jobs_document_id ON processing_jobs (document_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS processing_jobs")
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.execute("DROP TABLE IF EXISTS documents")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS document_status")
    op.execute("DROP TYPE IF EXISTS processing_stage")
    op.execute("DROP TYPE IF EXISTS job_status")
