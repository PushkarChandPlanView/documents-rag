import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_producer: AIOKafkaProducer | None = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: v if isinstance(v, bytes) else json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            max_batch_size=16384,
            linger_ms=5,
        )
        await _producer.start()
    return _producer


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def publish(topic: str, payload: bytes, key: str | None = None) -> None:
    producer = await get_producer()
    try:
        await producer.send_and_wait(topic=topic, value=payload, key=key)
        logger.debug("Published to topic=%s key=%s", topic, key)
    except Exception as exc:
        logger.warning("Publish failed (%s), resetting producer and retrying once.", exc)
        await stop_producer()
        producer = await get_producer()
        try:
            await producer.send_and_wait(topic=topic, value=payload, key=key)
            logger.debug("Published to topic=%s key=%s (after reset)", topic, key)
        except Exception as retry_exc:
            logger.error("Failed to publish to topic=%s after reset: %s", topic, retry_exc)
            raise
