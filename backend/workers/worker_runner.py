"""
Entry point for all workers.
Select worker type via WORKER_TYPE env var:
  text_extraction | chunking | embedding | summarization
"""
import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

WORKER_MAP = {
    "text_extraction": "text_extraction.consumer.TextExtractionConsumer",
    "chunking": "chunking.consumer.ChunkingConsumer",
    "embedding": "embedding.consumer.EmbeddingConsumer",
    "summarization": "summarization.consumer.SummarizationConsumer",
}


def import_consumer(dotted_path: str):
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


async def main():
    worker_type = os.environ.get("WORKER_TYPE", "").strip()
    if not worker_type:
        logger.error("WORKER_TYPE environment variable is not set")
        sys.exit(1)

    if worker_type not in WORKER_MAP:
        logger.error("Unknown WORKER_TYPE: %s. Valid options: %s", worker_type, list(WORKER_MAP.keys()))
        sys.exit(1)

    logger.info("Starting worker: %s", worker_type)
    ConsumerClass = import_consumer(WORKER_MAP[worker_type])
    consumer = ConsumerClass()
    await consumer.start()


if __name__ == "__main__":
    asyncio.run(main())
