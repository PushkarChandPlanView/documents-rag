"""Merge folders and documents into a single items table (STI) + versioned summaries

Revision ID: 003
Revises: 002
Create Date: 2026-05-28
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create items table (no summary column — that lives in document_summaries)
    op.execute("""
        CREATE TABLE items (
            id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            type            VARCHAR(20)  NOT NULL,
            user_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name            VARCHAR(500) NOT NULL,
            parent_id       UUID         REFERENCES items(id) ON DELETE SET NULL,
            mime_type       VARCHAR(200),
            file_size_bytes INTEGER,
            minio_key       VARCHAR(1000),
            source_url      VARCHAR(2000),
            status          VARCHAR(50),
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
            CONSTRAINT items_type_check CHECK (type IN ('folder', 'document'))
        )
    """)
    op.execute("CREATE INDEX ix_items_user_id   ON items (user_id)")
    op.execute("CREATE INDEX ix_items_type      ON items (type)")
    op.execute("CREATE INDEX ix_items_parent_id ON items (parent_id)")
    op.execute("CREATE INDEX ix_items_status    ON items (status)")

    # 2. Create versioned summaries table
    op.execute("""
        CREATE TABLE document_summaries (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID        NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            summary     TEXT        NOT NULL,
            model       VARCHAR(200),
            strategy    VARCHAR(50),
            version     INTEGER     NOT NULL DEFAULT 1,
            is_active   BOOLEAN     NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_document_summaries_document_id ON document_summaries (document_id)")
    op.execute("CREATE INDEX ix_document_summaries_is_active   ON document_summaries (is_active)")

    # 3. Migrate folders → items (preserve UUIDs)
    op.execute("""
        INSERT INTO items (id, type, user_id, name, parent_id, created_at, updated_at)
        SELECT id, 'folder', user_id, name, parent_id, created_at, updated_at
        FROM folders
    """)

    # 4. Migrate documents → items (folder_id → parent_id; status cast to VARCHAR)
    op.execute("""
        INSERT INTO items (
            id, type, user_id, name, parent_id,
            mime_type, file_size_bytes, minio_key, source_url,
            status, created_at, updated_at
        )
        SELECT
            id, 'document', user_id, filename, folder_id,
            mime_type, file_size_bytes, minio_key, source_url,
            status::text, created_at, updated_at
        FROM documents
    """)

    # 5. Migrate existing summaries from documents into document_summaries
    op.execute("""
        INSERT INTO document_summaries (document_id, summary, is_active, created_at)
        SELECT id, summary, true, updated_at
        FROM documents
        WHERE summary IS NOT NULL
    """)

    # 6. Re-target processing_jobs FK → items
    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT IF EXISTS processing_jobs_document_id_fkey")
    op.execute("""
        ALTER TABLE processing_jobs
            ADD CONSTRAINT processing_jobs_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES items(id) ON DELETE CASCADE
    """)

    # 7. Re-target document_chunks FK → items
    op.execute("ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_document_id_fkey")
    op.execute("""
        ALTER TABLE document_chunks
            ADD CONSTRAINT document_chunks_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES items(id) ON DELETE CASCADE
    """)

    # 8. Drop old tables and the now-unused document_status enum
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    op.execute("DROP TABLE IF EXISTS folders  CASCADE")
    op.execute("DROP TYPE  IF EXISTS document_status")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE document_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

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
    op.execute("""
        INSERT INTO folders (id, user_id, name, parent_id, created_at, updated_at)
        SELECT id, user_id, name, parent_id, created_at, updated_at
        FROM items WHERE type = 'folder'
    """)

    op.execute("""
        CREATE TABLE documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename VARCHAR(500) NOT NULL,
            minio_key VARCHAR(1000) NOT NULL DEFAULT '',
            mime_type VARCHAR(200) NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            status document_status NOT NULL DEFAULT 'PENDING',
            folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
            source_url VARCHAR(2000),
            summary TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    # Restore documents; pull latest active summary back into the summary column
    op.execute("""
        INSERT INTO documents (
            id, user_id, filename, minio_key, mime_type, file_size_bytes,
            status, folder_id, source_url, summary, created_at, updated_at
        )
        SELECT
            i.id, i.user_id, i.name, COALESCE(i.minio_key, ''),
            i.mime_type, COALESCE(i.file_size_bytes, 0),
            i.status::document_status, i.parent_id, i.source_url,
            (SELECT s.summary FROM document_summaries s
             WHERE s.document_id = i.id AND s.is_active ORDER BY s.created_at DESC LIMIT 1),
            i.created_at, i.updated_at
        FROM items i WHERE i.type = 'document'
    """)

    op.execute("ALTER TABLE processing_jobs DROP CONSTRAINT IF EXISTS processing_jobs_document_id_fkey")
    op.execute("""
        ALTER TABLE processing_jobs
            ADD CONSTRAINT processing_jobs_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    """)
    op.execute("ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_document_id_fkey")
    op.execute("""
        ALTER TABLE document_chunks
            ADD CONSTRAINT document_chunks_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    """)

    op.execute("DROP TABLE IF EXISTS document_summaries CASCADE")
    op.execute("DROP TABLE IF EXISTS items CASCADE")
