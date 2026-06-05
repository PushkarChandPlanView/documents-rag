"""
Chunking Worker
Consumes: text_extracted
Publishes: document_chunked
"""
import logging
import uuid

from aiokafka import ConsumerRecord
from sqlalchemy import text as sql_text

from base.base_consumer import BaseConsumer
from base.base_producer import publish
from config import get_settings
from shared import db_client, minio_client
from shared.schemas import DocumentChunkedEvent, TextExtractedEvent, Topics
from .strategies import recursive_character, semantic

logger = logging.getLogger(__name__)
settings = get_settings()


class ChunkingConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=settings.kafka_topic_text_extracted,
            group_id=settings.kafka_consumer_group_chunking,
        )

    async def process_message(self, message: ConsumerRecord) -> None:
        event = TextExtractedEvent.from_json(message.value)
        doc_id = str(event.document_id)
        logger.info("Chunking document_id=%s", doc_id)

        async with await db_client.get_session() as session:
            await session.execute(
                sql_text(
                    "UPDATE processing_jobs SET status = 'IN_PROGRESS', started_at = now() "
                    "WHERE document_id = :doc_id AND stage = 'CHUNKING'"
                ).bindparams(doc_id=event.document_id)
            )
            await session.commit()

        # Download extracted text
        text_bytes = minio_client.download(settings.minio_bucket_processed, event.text_minio_key)
        text = text_bytes.decode("utf-8", errors="replace")

        # Choose chunking strategy
        if len(text) > settings.semantic_chunk_threshold_chars:
            chunks = semantic.chunk(text)
            strategy = "semantic"
        else:
            chunks = recursive_character.chunk(text)
            strategy = "recursive_character"

        logger.info("Created %d chunks using strategy=%s for document_id=%s", len(chunks), strategy, doc_id)

        if not chunks:
            # No text could be extracted — mark everything FAILED and stop the pipeline
            logger.warning("No chunks produced for document_id=%s — marking FAILED", doc_id)
            async with await db_client.get_session() as session:
                await session.execute(
                    sql_text(
                        "UPDATE processing_jobs SET status = 'FAILED', completed_at = now() "
                        "WHERE document_id = :doc_id AND stage = 'CHUNKING'"
                    ).bindparams(doc_id=event.document_id)
                )
                await session.execute(
                    sql_text(
                        "UPDATE items SET status = 'FAILED', updated_at = now() WHERE id = :doc_id"
                    ).bindparams(doc_id=event.document_id)
                )
                await session.commit()
            return

        # Bulk insert all chunks in a single query
        async with await db_client.get_session() as session:
            params: dict = {"document_id": event.document_id}
            placeholders = []
            for i, chunk in enumerate(chunks):
                params[f"id{i}"] = uuid.uuid4()
                params[f"ci{i}"] = chunk.chunk_index
                params[f"t{i}"] = chunk.text
                params[f"cc{i}"] = chunk.char_count
                params[f"pn{i}"] = chunk.page_number
                placeholders.append(f"(:id{i}, :document_id, :ci{i}, :t{i}, :cc{i}, :pn{i})")
            await session.execute(
                sql_text(
                    "INSERT INTO document_chunks (id, document_id, chunk_index, text, char_count, page_number) "
                    "VALUES " + ", ".join(placeholders)
                ).bindparams(**params)
            )
            await session.execute(
                sql_text(
                    "UPDATE processing_jobs SET status = 'COMPLETED', completed_at = now() "
                    "WHERE document_id = :doc_id AND stage = 'CHUNKING'"
                ).bindparams(doc_id=event.document_id)
            )
            await session.commit()

        # Publish next event
        next_event = DocumentChunkedEvent(
            document_id=event.document_id,
            user_id=event.user_id,
            chunk_count=len(chunks),
            chunking_strategy=strategy,
        )
        await publish(topic=Topics.DOCUMENT_CHUNKED, event=next_event, key=doc_id)
        logger.info("Chunking complete for document_id=%s chunks=%d", doc_id, len(chunks))
