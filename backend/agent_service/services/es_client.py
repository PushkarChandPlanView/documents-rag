"""HTTP client that calls rag_service /search — keeps agent_service decoupled from ES."""
import logging
from typing import Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def search(
    query: str,
    user_id: str,
    source_types: Optional[list[str]] = None,
    top_k: int = 10,
) -> list[dict]:
    """Call rag_service /search and return list of chunk dicts."""
    payload = {
        "query": query,
        "user_id": user_id,
        "top_k": top_k,
        "mode": "hybrid",
    }
    if source_types:
        payload["source_types"] = source_types

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.rag_service_url}/search", json=payload)
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as exc:
        logger.error("es_client search error: %s", exc)
        return []
