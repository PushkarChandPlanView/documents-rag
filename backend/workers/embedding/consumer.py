"""
Embedding Worker
Consumes: document_chunked
Publishes: embeddings_generated
Writes to: ChromaDB
"""
import logging
from uuid import UUID

from aiokafka import ConsumerRecord
from sqlalchemy import text as sql_text

from base.base_consumer import BaseConsumer
from base.base_producer import publish
from config import get_settings
from shared import chroma_client, db_client
from shared.schemas import DocumentChunkedEvent, EmbeddingsGeneratedEvent, Topics
from .ollama_embedder import embed_batch

logger = logging.getLogger(__name__)
settings = get_settings()


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

        # Fetch document name and file type
        async with await db_client.get_session() as session:
            doc_result = await session.execute(
                sql_text(
                    "SELECT filename, file_type FROM documents WHERE id = :doc_id"
                ).bindparams(doc_id=event.document_id)
            )
            doc_row = doc_result.fetchone()

        document_name = doc_row.filename if doc_row else doc_id
        file_type = doc_row.file_type if doc_row else "unknown"

        chunk_ids = [str(row.id) for row in rows]
        chunk_texts = [row.text for row in rows]
        chunk_indices = [row.chunk_index for row in rows]
        page_numbers = [row.page_number for row in rows]
        char_counts = [row.char_count for row in rows]
        total_chunks = len(rows)

        # Generate embeddings via Ollama
        embeddings = await embed_batch(chunk_texts)
        embedding_dim = len(embeddings[0]) if embeddings else 0

        # Write to ChromaDB
        collection = chroma_client.get_or_create_collection()
        metadatas = [
            {
                "document_id": doc_id,
                "user_id": str(event.user_id),
                "chunk_index": chunk_indices[i],
                "page_number": page_numbers[i] if page_numbers[i] is not None else -1,
                "document_name": document_name,
                "file_type": file_type,
                "char_count": char_counts[i] if char_counts[i] is not None else 0,
                "total_chunks": total_chunks,
            }
            for i in range(len(chunk_ids))
        ]
        collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

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
