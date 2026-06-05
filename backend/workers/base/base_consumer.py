"""
Abstract base class for all Kafka consumers.
Handles:
  - Connection lifecycle (start/stop)
  - Retry logic (up to MAX_RETRIES per message before DLQ)
  - Dead Letter Queue publishing
  - Graceful shutdown on SIGTERM
"""
import asyncio
import json
import logging
import signal
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord

from config import get_settings
from shared.schemas import DocumentErrorEvent

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_RETRIES = 3


class BaseConsumer(ABC):
    def __init__(self, topic: str, group_id: str) -> None:
        self.topic = topic
        self.group_id = group_id
        self._consumer: AIOKafkaConsumer | None = None
        self._dlq_producer: AIOKafkaProducer | None = None
        self._running = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=False,   # manual commit after processing
            auto_offset_reset="earliest",
            max_poll_records=1,
            session_timeout_ms=120_000,      # broker waits 2 min before evicting
            heartbeat_interval_ms=10_000,    # send heartbeat every 10s
            max_poll_interval_ms=1_800_000,  # 30 min — covers slow Ollama inference
        )
        self._dlq_producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: v if isinstance(v, bytes) else json.dumps(v).encode(),
        )

        await self._consumer.start()
        await self._dlq_producer.start()
        self._running = True

        # Register SIGTERM for graceful shutdown
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.stop()))

        logger.info("Consumer started: topic=%s group=%s", self.topic, self.group_id)
        await self._consume_loop()

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        if self._dlq_producer:
            await self._dlq_producer.stop()
        logger.info("Consumer stopped: topic=%s", self.topic)

    async def _consume_loop(self) -> None:
        async for message in self._consumer:
            if not self._running:
                break
            await self._handle_with_retry(message)

    async def _handle_with_retry(self, message: ConsumerRecord) -> None:
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self.process_message(message)
                await self._consumer.commit()
                return
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Error processing message (attempt %d/%d): topic=%s partition=%d offset=%d: %s",
                    attempt, MAX_RETRIES, message.topic, message.partition, message.offset, exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff

        # Exhausted retries → send to DLQ
        logger.error(
            "Message sent to DLQ after %d retries: topic=%s offset=%d",
            MAX_RETRIES, message.topic, message.offset,
        )
        await self._send_to_dlq(message, last_exc)
        await self._consumer.commit()  # commit so we don't reprocess

    async def _send_to_dlq(self, message: ConsumerRecord, error: Exception | None) -> None:
        try:
            error_event = DocumentErrorEvent(
                source_topic=message.topic,
                error_type=type(error).__name__ if error else "Unknown",
                error_message=str(error) if error else "Unknown error",
                original_payload=message.value.decode("utf-8") if message.value else "",
                failed_at=datetime.now(timezone.utc),
                retry_count=MAX_RETRIES,
            )
            await self._dlq_producer.send_and_wait(
                topic=settings.kafka_topic_dlq,
                value=error_event.to_json(),
            )
        except Exception as dlq_exc:
            logger.error("Failed to send to DLQ: %s", dlq_exc)

    @abstractmethod
    async def process_message(self, message: ConsumerRecord) -> None:
        """Implement message processing logic. Raise on failure."""
        ...
