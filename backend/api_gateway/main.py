import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import auth, chat, documents, health
from services import kafka_producer, storage_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting API Gateway...")

    # Ensure MinIO buckets exist
    storage_service.ensure_buckets()
    logger.info("MinIO buckets ready.")

    # Start Kafka producer
    await kafka_producer.get_producer()
    logger.info("Kafka producer ready.")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    await kafka_producer.stop_producer()
    await engine.dispose()
    logger.info("API Gateway shut down.")


app = FastAPI(
    title="Document Intelligence API",
    description="Self-hosted AI document storage, search, and summarization",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
