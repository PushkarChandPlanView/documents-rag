"""
pgvector client — replaces ChromaDB for vector storage in the worker pipeline.

Vectors are stored in the `document_embeddings` table (created by init.sql).
The chunk text itself lives in `document_chunks`; we just store metadata here
so the RAG service can JOIN back for the original text at query time.
"""
import logging

from sqlalchemy import text as sql_text

from shared import db_client

logger = logging.getLogger(__name__)


async def upsert_embeddings(rows: list[dict]) -> None:
    """
    Insert or update embeddings for a batch of chunks.

    Each row dict must contain:
        chunk_id      : str (UUID)
        document_id   : str (UUID)
        user_id       : str (UUID)
        chunk_index   : int
        page_number   : int | None
        document_name : str
        file_type     : str
        char_count    : int
        token_count   : int
        total_chunks  : int
        embedding     : list[float]
    """
    if not rows:
        return

    async with await db_client.get_session() as session:
        for row in rows:
            embedding_str = "[" + ",".join(str(x) for x in row["embedding"]) + "]"
            await session.execute(
                sql_text("""
                    INSERT INTO document_embeddings
                        (chunk_id, document_id, user_id, chunk_index, page_number,
                         document_name, file_type, char_count, token_count, total_chunks,
                         embedding)
                    VALUES
                        (CAST(:chunk_id AS uuid), CAST(:document_id AS uuid), CAST(:user_id AS uuid),
                         :chunk_index, :page_number,
                         :document_name, :file_type, :char_count, :token_count, :total_chunks,
                         CAST(:embedding AS vector))
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        embedding     = EXCLUDED.embedding,
                        chunk_index   = EXCLUDED.chunk_index,
                        page_number   = EXCLUDED.page_number,
                        document_name = EXCLUDED.document_name,
                        file_type     = EXCLUDED.file_type,
                        char_count    = EXCLUDED.char_count,
                        token_count   = EXCLUDED.token_count,
                        total_chunks  = EXCLUDED.total_chunks
                """),
                {
                    "chunk_id":      row["chunk_id"],
                    "document_id":   row["document_id"],
                    "user_id":       row["user_id"],
                    "chunk_index":   row["chunk_index"],
                    "page_number":   row.get("page_number"),
                    "document_name": row.get("document_name", ""),
                    "file_type":     row.get("file_type", ""),
                    "char_count":    row.get("char_count", 0),
                    "token_count":   row.get("token_count", 0),
                    "total_chunks":  row.get("total_chunks", 0),
                    "embedding":     embedding_str,
                },
            )
        await session.commit()
    logger.debug("Upserted %d embeddings into pgvector", len(rows))


async def delete_by_document(document_id: str) -> None:
    """Remove all embedding vectors for a given document."""
    async with await db_client.get_session() as session:
        result = await session.execute(
            sql_text("DELETE FROM document_embeddings WHERE document_id = :doc_id::uuid"),
            {"doc_id": document_id},
        )
        await session.commit()
    logger.info("Deleted embeddings for document_id=%s", document_id)
