"""
Compliance Worker
Two consumers:
  ComplianceConsumer     — Consumes: summary_generated   (group: compliance-workers)
  ComplianceAfterRagConsumer — Consumes: embeddings_generated (group: compliance-rag-workers)

Both run all active compliance rules against the document and persist results.
ComplianceAfterRagConsumer runs without a summary; LLM-based rules receive an
empty string and the engine degrades gracefully.
"""
import logging

from aiokafka import ConsumerRecord

from base.base_consumer import BaseConsumer
from config import get_settings
from shared import db_client
from shared.schemas import EmbeddingsGeneratedEvent, SummaryGeneratedEvent

from .engine import run_compliance_check

logger = logging.getLogger(__name__)
settings = get_settings()


class ComplianceConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=settings.kafka_topic_summary_generated,
            group_id=settings.kafka_consumer_group_compliance,
        )

    async def process_message(self, message: ConsumerRecord) -> None:
        event = SummaryGeneratedEvent.from_json(message.value)
        logger.info("compliance: checking document_id=%s", event.document_id)
        async with await db_client.get_session() as session:
            await run_compliance_check(event.document_id, session)
        logger.info("compliance: done document_id=%s", event.document_id)


class ComplianceAfterRagConsumer(BaseConsumer):
    """Triggers compliance as soon as the RAG pipeline (embedding) completes."""

    def __init__(self):
        super().__init__(
            topic=settings.kafka_topic_embeddings_generated,
            group_id=settings.kafka_consumer_group_compliance_rag,
        )

    async def process_message(self, message: ConsumerRecord) -> None:
        event = EmbeddingsGeneratedEvent.from_json(message.value)
        logger.info("compliance(rag): checking document_id=%s", event.document_id)
        async with await db_client.get_session() as session:
            await run_compliance_check(event.document_id, session)
        logger.info("compliance(rag): done document_id=%s", event.document_id)
