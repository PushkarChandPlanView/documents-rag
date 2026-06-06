"""
Embedding Worker
Consumes: document_chunked
Publishes: embeddings_generated
Writes to: pgvector (PostgreSQL document_embeddings table)
"""
import logging
from uuid import UUID

import tiktoken
from aiokafka import ConsumerRecord
from sqlalchemy import text as sql_text

from base.base_consumer import BaseConsumer
from base.base_producer import publish
from config import get_settings
from shared import pgvector_client, db_client
from shared.providers import llm_factory
from shared.schemas import DocumentChunkedEvent, EmbeddingsGeneratedEvent, Topics

logger = logging.getLogger(__name__)
settings = get_settings()

_enc = tiktoken.get_encoding("cl100k_base")


class EmbeddingConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=settings.kafka_topic_document_chunked,
            group_id=settings.kafka_consumer_group_embedding,
        )

    async def process_message(self, message: ConsumerRecord) -> None:
        event = DocumentChunkedEvent.from_json(message.value)
        doc_id = str(event.document_id)
        logger.info("Embedding document_id=%s chunks=%d", doc_id, event.chunk_count)

        async with await db_client.get_session() as session:
            await session.execute(
                sql_text(
                    "UPDATE processing_jobs SET status = 'IN_PROGRESS', started_at = now() "
                    "WHERE document_id = :doc_id AND stage = 'EMBEDDING'"
                ).bindparams(doc_id=event.document_id)
            )
            await session.commit()

        # Fetch all chunks from PostgreSQL
        async with await db_client.get_session() as session:
            result = await session.execute(
                sql_text(
                    "SELECT id, chunk_index, text, page_number, char_count "
                    "FROM document_chunks WHERE document_id = :doc_id ORDER BY chunk_index"
                ).bindparams(doc_id=event.document_id)
            )
            rows = result.fetchall()

        if not rows:
            raise ValueError(f"No chunks found for document_id={doc_id}")

        # Fetch document name and mime type from items table
        async with await db_client.get_session() as session:
            doc_result = await session.execute(
                sql_text(
                    "SELECT name, mime_type FROM documents WHERE id = :doc_id"
                ).bindparams(doc_id=event.document_id)
            )
            doc_row = doc_result.fetchone()

        document_name = doc_row.name if doc_row else doc_id
        file_type = doc_row.mime_type if doc_row else "unknown"

        chunk_ids = [str(row.id) for row in rows]
        chunk_texts = [row.text for row in rows]
        chunk_indices = [row.chunk_index for row in rows]
        page_numbers = [row.page_number for row in rows]
        char_counts = [row.char_count for row in rows]
        total_chunks = len(rows)

        # Build contextual prefix texts for embedding.
        # The prefix anchors each chunk to its document and position, improving
        # retrieval accuracy without polluting the stored document text.
        contextualized = [
            f"Document: {document_name} ({file_type})\n\nChunk {chunk_indices[i] + 1} of {total_chunks}:\n{chunk_texts[i]}"
            for i in range(total_chunks)
        ]

        # Generate embeddings via configured provider (uses contextualized texts)
        embeddings = await llm_factory.embed_batch(contextualized)
        embedding_dim = len(embeddings[0]) if embeddings else 0

        # Compute token counts on original chunk texts (what the LLM will read)
        token_counts = [len(_enc.encode(t)) for t in chunk_texts]

        # Write to pgvector — store ORIGINAL chunk text, not the prefixed version
        rows = [
            {
                "chunk_id":      chunk_ids[i],
                "document_id":   doc_id,
                "user_id":       str(event.user_id),
                "chunk_index":   chunk_indices[i],
                "page_number":   page_numbers[i] if page_numbers[i] is not None else None,
                "document_name": document_name,
                "file_type":     file_type,
                "char_count":    char_counts[i] if char_counts[i] is not None else 0,
                "token_count":   token_counts[i],
                "total_chunks":  total_chunks,
                "embedding":     embeddings[i],
            }
            for i in range(len(chunk_ids))
        ]
        await pgvector_client.upsert_embeddings(rows)

        async with await db_client.get_session() as session:
            await session.execute(
                sql_text(
                    "UPDATE processing_jobs SET status = 'COMPLETED', completed_at = now() "
                    "WHERE document_id = :doc_id AND stage = 'EMBEDDING'"
                ).bindparams(doc_id=event.document_id)
            )
            await session.commit()

        next_event = EmbeddingsGeneratedEvent(
            document_id=event.document_id,
            user_id=event.user_id,
            vector_count=len(chunk_ids),
            embedding_model=settings.ollama_embed_model,
            embedding_dim=embedding_dim,
        )
        await publish(topic=Topics.EMBEDDINGS_GENERATED, event=next_event, key=doc_id)
        logger.info("Embedding complete for document_id=%s vectors=%d dim=%d", doc_id, len(chunk_ids), embedding_dim)
