import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers import health, query

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


class _NoHealthCheck(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "GET /health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_NoHealthCheck())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RAG Service starting...")
    yield
    logger.info("RAG Service shut down.")


app = FastAPI(
    title="RAG Service",
    description="Internal RAG query service — not exposed publicly",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(query.router)
