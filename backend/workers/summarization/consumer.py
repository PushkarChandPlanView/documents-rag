"""
Summarization Worker
Consumes: embeddings_generated
Publishes: summary_generated
Updates: documents.summary, documents.status → COMPLETED
"""
import logging

import tiktoken
from aiokafka import ConsumerRecord
from sqlalchemy import text as sql_text

from base.base_consumer import BaseConsumer
from base.base_producer import publish
from config import get_settings
from shared import db_client
from shared.schemas import EmbeddingsGeneratedEvent, SummaryGeneratedEvent, Topics
from .strategies import map_reduce, single_pass

logger = logging.getLogger(__name__)
settings = get_settings()

TOKEN_THRESHOLD = 8000


def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


class SummarizationConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=settings.kafka_topic_embeddings_generated,
            group_id=settings.kafka_consumer_group_summarization,
        )

    async def process_message(self, message: ConsumerRecord) -> None:
        event = EmbeddingsGeneratedEvent.from_json(message.value)
        doc_id = str(event.document_id)
        logger.info("Summarizing document_id=%s", doc_id)

        async with await db_client.get_session() as session:
            await session.execute(
                sql_text(
                    "UPDATE processing_jobs SET status = 'IN_PROGRESS', started_at = now() "
                    "WHERE document_id = :doc_id AND stage = 'SUMMARIZATION'"
                ).bindparams(doc_id=event.document_id)
            )
            await session.commit()

        # Fetch chunk texts from PostgreSQL
        async with await db_client.get_session() as session:
            result = await session.execute(
                sql_text(
                    "SELECT text FROM document_chunks WHERE document_id = :doc_id ORDER BY chunk_index"
                ).bindparams(doc_id=event.document_id)
            )
            rows = result.fetchall()

        chunk_texts = [row.text for row in rows]
        if not chunk_texts:
            raise ValueError(f"No chunks found for document_id={doc_id}")

        full_text = " ".join(chunk_texts)
        token_count = count_tokens(full_text)

        if token_count <= TOKEN_THRESHOLD:
            summary = await single_pass.summarize(full_text)
            strategy = "single_pass"
        else:
            summary = await map_reduce.summarize(chunk_texts)
            strategy = "map_reduce"

        logger.info(
            "Summary generated for document_id=%s strategy=%s tokens=%d",
            doc_id, strategy, token_count,
        )

        # Persist summary and mark document COMPLETED
        async with await db_client.get_session() as session:
            await session.execute(
                sql_text(
                    "UPDATE documents SET summary = :summary, status = 'COMPLETED', updated_at = now() "
                    "WHERE id = :doc_id"
                ).bindparams(summary=summary, doc_id=event.document_id)
            )
            await session.execute(
                sql_text(
                    "UPDATE processing_jobs SET status = 'COMPLETED', completed_at = now() "
                    "WHERE document_id = :doc_id AND stage = 'SUMMARIZATION'"
                ).bindparams(doc_id=event.document_id)
            )
            await session.commit()

        next_event = SummaryGeneratedEvent(
            document_id=event.document_id,
            user_id=event.user_id,
            summary_length=len(summary),
            strategy=strategy,
        )
        await publish(topic=Topics.SUMMARY_GENERATED, event=next_event, key=doc_id)
        logger.info("Summarization complete for document_id=%s", doc_id)
