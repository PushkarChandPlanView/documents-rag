"""
Embedding generation via Ollama /api/embeddings endpoint.
Concurrent: fires up to CONCURRENCY requests simultaneously using asyncio.gather.
"""
import asyncio

import httpx

from config import get_settings

settings = get_settings()

# Max concurrent embedding requests to Ollama — match OLLAMA_NUM_PARALLEL
CONCURRENCY = 8


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed texts concurrently. Returns list of float vectors in input order."""
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _embed_one(client: httpx.AsyncClient, text: str) -> list[float]:
        async with sem:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    async with httpx.AsyncClient(timeout=120) as client:
        return list(await asyncio.gather(*[_embed_one(client, t) for t in texts]))
