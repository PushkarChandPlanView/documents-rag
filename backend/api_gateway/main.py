import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config import get_settings
from dependencies import AsyncSessionLocal, engine
from models.user import User
import models.comment  # noqa: F401 — registers Comment/CommentLike with Base.metadata
from routers import auth, chat, compliance, documents, edits, folders, health, search
from routers.comments import router as comments_router
from services import auth_service, kafka_producer, storage_service
from services.seed_compliance import seed_compliance_rules

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


async def _auto_seed() -> None:
    """Create the default admin user if it doesn't already exist."""
    from sqlalchemy.exc import IntegrityError
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            try:
                user = await auth_service.create_user(db, "admin@example.com", "changeme")
                logger.info("Auto-seeded default user: %s", user.email)
            except IntegrityError:
                await db.rollback()
                logger.info("Default user already exists (seeded by another worker), skipping.")


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

    # Seed default user and compliance rules on fresh database
    await _auto_seed()
    await seed_compliance_rules()

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
app.include_router(folders.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(edits.router, prefix="/api")
app.include_router(comments_router)
