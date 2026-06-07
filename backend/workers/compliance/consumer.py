"""
Compliance Worker
Consumes: summary_generated (new consumer group: compliance-workers)
Runs all active compliance rules against the document and persists results.
"""
import logging

from aiokafka import ConsumerRecord

from base.base_consumer import BaseConsumer
from config import get_settings
from shared import db_client
from shared.schemas import SummaryGeneratedEvent

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
