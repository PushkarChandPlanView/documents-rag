"""
Embedding generation via Ollama.
Uses /api/embed (batch, Ollama ≥ 0.1.31) for efficiency.
Falls back to /api/embeddings (one-at-a-time) if batch endpoint returns 400/404.
"""
import asyncio
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BATCH_SIZE = 32
CONCURRENCY = 4   # concurrent batch requests
_use_batch_api: bool | None = None  # resolved on first call


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed all texts. Auto-detects batch vs legacy API on first call."""
    global _use_batch_api
    if not texts:
        return []

    async with httpx.AsyncClient(timeout=300) as client:
        if _use_batch_api is None:
            _use_batch_api = await _probe_batch_api(client)
            logger.info("Ollama embedding API: %s", "batch /api/embed" if _use_batch_api else "legacy /api/embeddings")

        if _use_batch_api:
            return await _embed_batch_api(client, texts)
        else:
            return await _embed_legacy_api(client, texts)


async def _probe_batch_api(client: httpx.AsyncClient) -> bool:
    """Return True if /api/embed is available and working."""
    try:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/embed",
            json={"model": settings.ollama_embed_model, "input": ["test"]},
            timeout=15,
        )
        return resp.status_code == 200
    except Exception:
        return False


async def _embed_batch_api(client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
    batches = [texts[i:i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]
    completed = 0
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _one_batch(batch: list[str]) -> list[list[float]]:
        nonlocal completed
        async with sem:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": batch},
            )
            resp.raise_for_status()
            completed += len(batch)
            pct = int(completed / len(texts) * 100)
            logger.info("Embedding progress: %d/%d chunks (%d%%)", completed, len(texts), pct)
            return resp.json()["embeddings"]

    results = await asyncio.gather(*[_one_batch(b) for b in batches])
    return [vec for batch in results for vec in batch]


async def _embed_legacy_api(client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
    completed = 0
    sem = asyncio.Semaphore(8)

    async def _one(text: str, idx: int) -> tuple[int, list[float]]:
        nonlocal completed
        async with sem:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": text},
            )
            resp.raise_for_status()
            completed += 1
            pct = int(completed / len(texts) * 100)
            logger.info("Embedding progress: %d/%d chunks (%d%%)", completed, len(texts), pct)
            return idx, resp.json()["embedding"]

    results = await asyncio.gather(*[_one(t, i) for i, t in enumerate(texts)])
    results.sort(key=lambda x: x[0])
    return [vec for _, vec in results]
