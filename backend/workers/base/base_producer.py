import json
import logging

from aiokafka import AIOKafkaProducer

from config import get_settings
from shared.schemas import KafkaMessage

logger = logging.getLogger(__name__)
settings = get_settings()

_producer: AIOKafkaProducer | None = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: v if isinstance(v, bytes) else json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
            acks="all",
            enable_idempotence=True,
        )
        await _producer.start()
    return _producer


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def publish(topic: str, event: KafkaMessage, key: str | None = None) -> None:
    producer = await get_producer()
    await producer.send_and_wait(topic=topic, value=event.to_json(), key=key)
    logger.debug("Published event to topic=%s key=%s", topic, key)
