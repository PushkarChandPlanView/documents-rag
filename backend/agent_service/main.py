"""agent_service — FastAPI app for agent CRUD and execution."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import agents

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
