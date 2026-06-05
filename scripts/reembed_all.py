#!/usr/bin/env python3
"""
Re-embedding migration script.

USAGE:
    python scripts/reembed_all.py [--dry-run] [--batch-size N]

PURPOSE:
    Run this once after changing OLLAMA_EMBED_MODEL in .env (e.g. nomic-embed-text
    → mxbai-embed-large) or when migrating from ChromaDB to pgvector.
    This script:

      1. Queries ALL document chunks from PostgreSQL
      2. Groups chunks by document and re-embeds with contextual prefixes
         (mirrors the logic in backend/workers/embedding/consumer.py)
      3. Upserts new vectors into the `document_embeddings` table in PostgreSQL
         (idempotent — safe to re-run after a partial failure)

PREREQUISITES:
    pip install psycopg2-binary httpx tiktoken python-dotenv

    The Ollama model must already be pulled:
        docker exec document-summarizer-ollama-1 ollama pull nomic-embed-text

    Stop the embedding worker first to prevent concurrent writes:
        docker compose stop worker_embedding

    Run from the project root so .env is found automatically:
        python scripts/reembed_all.py --dry-run   # verify counts
        python scripts/reembed_all.py             # live migration

    NOTE: If the vector dimension of your new model differs from the current
    `document_embeddings.embedding` column dimension, run this first:
        ALTER TABLE document_embeddings ALTER COLUMN embedding TYPE vector(<new_dim>);
        DROP INDEX IF EXISTS document_embeddings_embedding_idx;
        CREATE INDEX document_embeddings_embedding_idx
            ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

PORTS (host-mapped, per docker-compose.yml):
    PostgreSQL → localhost:5433
    Ollama     → localhost:11434
"""
import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

import httpx
import tiktoken
from dotenv import load_dotenv

# Load .env from project root (script lives in scripts/, run from project root)
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Configuration ─────────────────────────────────────────────────────────────

def _pg_url() -> str:
    """Convert asyncpg URL from .env to a psycopg2-compatible DSN."""
    url = os.environ.get("POSTGRES_URL", "postgresql+asyncpg://docstore:changeme@postgres:5432/docstore")
    # Strip SQLAlchemy driver prefix
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    # Remap docker-internal hostname to host-mapped port
    url = url.replace("@postgres:5432/", "@localhost:5433/")
    return url


POSTGRES_URL        = _pg_url()
OLLAMA_BASE_URL     = (
    os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    .replace("ollama:11434", "localhost:11434")               # remap docker hostname
)
OLLAMA_EMBED_MODEL  = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CONCURRENCY         = 8  # matches ollama_embedder.py

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("reembed")
_enc = tiktoken.get_encoding("cl100k_base")


# ── Ollama embedding ──────────────────────────────────────────────────────────

async def _embed_one(client: httpx.AsyncClient, sem: asyncio.Semaphore, text: str) -> list[float]:
    async with sem:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=120) as client:
        return list(await asyncio.gather(*[_embed_one(client, sem, t) for t in texts]))


# ── PostgreSQL (sync via psycopg2) ────────────────────────────────────────────

def fetch_all_chunks() -> list[dict]:
    """Return all document chunks joined with document metadata, ordered by document/chunk."""
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(POSTGRES_URL)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.chunk_index,
                    dc.text,
                    dc.char_count,
                    dc.page_number,
                    d.filename   AS document_name,
                    d.mime_type  AS file_type,
                    d.user_id
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                ORDER BY dc.document_id, dc.chunk_index
            """)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def upsert_embeddings_sync(conn, rows: list[dict]) -> None:
    """Insert or update a batch of embedding rows into document_embeddings."""
    import psycopg2.extras
    with conn.cursor() as cur:
        for row in rows:
            embedding_str = "[" + ",".join(str(x) for x in row["embedding"]) + "]"
            cur.execute(
                """
                INSERT INTO document_embeddings
                    (chunk_id, document_id, user_id, chunk_index, page_number,
                     document_name, file_type, char_count, token_count, total_chunks,
                     embedding)
                VALUES
                    (%s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    embedding     = EXCLUDED.embedding,
                    chunk_index   = EXCLUDED.chunk_index,
                    page_number   = EXCLUDED.page_number,
                    document_name = EXCLUDED.document_name,
                    file_type     = EXCLUDED.file_type,
                    char_count    = EXCLUDED.char_count,
                    token_count   = EXCLUDED.token_count,
                    total_chunks  = EXCLUDED.total_chunks
                """,
                (
                    str(row["chunk_id"]),
                    str(row["document_id"]),
                    str(row["user_id"]),
                    row["chunk_index"],
                    row.get("page_number"),
                    row.get("document_name", ""),
                    row.get("file_type", ""),
                    row.get("char_count", 0),
                    row.get("token_count", 0),
                    row.get("total_chunks", 0),
                    embedding_str,
                ),
            )
    conn.commit()


def delete_all_embeddings(conn) -> None:
    """Wipe all rows from document_embeddings (equivalent to dropping a Chroma collection)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_embeddings")
    conn.commit()
    logger.info("Cleared document_embeddings table")


# ── Migration logic ───────────────────────────────────────────────────────────

def group_by_document(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(str(row["document_id"]), []).append(row)
    return groups


async def reembed_document(conn, doc_id: str, chunks: list[dict], dry_run: bool) -> int:
    """Embed all chunks for one document and upsert into pgvector. Returns vector count."""
    total         = len(chunks)
    document_name = chunks[0]["document_name"] or doc_id
    file_type     = chunks[0]["file_type"] or "unknown"
    chunk_texts   = [c["text"] for c in chunks]

    if dry_run:
        return total

    # Contextual prefix — mirrors embedding/consumer.py
    contextualized = [
        f"Document: {document_name} ({file_type})\n\nChunk {c['chunk_index'] + 1} of {total}:\n{c['text']}"
        for c in chunks
    ]

    embeddings = await embed_batch(contextualized)

    rows = [
        {
            "chunk_id":      str(chunks[i]["id"]),
            "document_id":   doc_id,
            "user_id":       str(chunks[i]["user_id"]),
            "chunk_index":   chunks[i]["chunk_index"],
            "page_number":   chunks[i]["page_number"],
            "document_name": document_name,
            "file_type":     file_type,
            "char_count":    chunks[i]["char_count"] if chunks[i]["char_count"] is not None else 0,
            "token_count":   len(_enc.encode(chunk_texts[i])),
            "total_chunks":  total,
            "embedding":     embeddings[i],
        }
        for i in range(total)
    ]

    # upsert is idempotent — re-running after a partial failure is safe
    upsert_embeddings_sync(conn, rows)
    return total


async def run(dry_run: bool, batch_size: int) -> None:
    import psycopg2
    logger.info("=== Re-embedding migration (pgvector) ===")
    logger.info("Model:      %s", OLLAMA_EMBED_MODEL)
    logger.info("PostgreSQL: %s", POSTGRES_URL.split("@")[-1])   # hide credentials
    logger.info("Dry run:    %s", dry_run)

    # 1. Fetch all chunks from Postgres
    logger.info("Fetching chunks from PostgreSQL...")
    t0 = time.monotonic()
    rows = fetch_all_chunks()
    logger.info("Fetched %d chunks across all documents (%.1fs)", len(rows), time.monotonic() - t0)

    if not rows:
        logger.warning("No chunks found — nothing to do.")
        return

    by_doc = group_by_document(rows)
    logger.info("Found %d documents to re-embed", len(by_doc))

    # 2. Open a persistent psycopg2 connection for upserts
    if not dry_run:
        conn = psycopg2.connect(POSTGRES_URL)
        logger.info("Clearing existing embeddings from document_embeddings...")
        delete_all_embeddings(conn)
    else:
        conn = None
        logger.info("[DRY RUN] Skipping embedding table reset")

    # 3. Re-embed document by document
    total_vectors = 0
    doc_ids = list(by_doc.keys())

    try:
        for batch_start in range(0, len(doc_ids), batch_size):
            batch = doc_ids[batch_start: batch_start + batch_size]
            for doc_id in batch:
                try:
                    count = await reembed_document(conn, doc_id, by_doc[doc_id], dry_run)
                    total_vectors += count
                except Exception as exc:
                    logger.error("Failed on document_id=%s: %s", doc_id, exc)
                    if not dry_run:
                        raise  # abort to avoid partial state

            completed = min(batch_start + batch_size, len(doc_ids))
            logger.info("Progress: %d/%d documents | %d vectors embedded", completed, len(doc_ids), total_vectors)
    finally:
        if conn:
            conn.close()

    action = "[DRY RUN] Would write" if dry_run else "Wrote"
    logger.info("=== Done: %s %d vectors across %d documents ===", action, total_vectors, len(doc_ids))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Count chunks and verify connectivity without writing to pgvector",
    )
    parser.add_argument(
        "--batch-size", type=int, default=20,
        help="Documents per progress log line (default: 20)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(dry_run=args.dry_run, batch_size=args.batch_size))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    except Exception as exc:
        logger.error("Migration failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
