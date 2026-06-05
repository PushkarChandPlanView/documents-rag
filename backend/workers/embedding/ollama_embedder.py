"""
Embedding generation via Ollama.
Uses /api/embed (batch, Ollama ≥ 0.1.31) for efficiency.
Falls back to /api/embeddings (one-at-a-time) if batch endpoint returns 400/404.

The API-detection result is cached per process but is RESET on a failed request
so that a transient 404 during Ollama startup never permanently breaks the worker.
"""
import asyncio
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BATCH_SIZE = 32
CONCURRENCY = 4   # concurrent batch requests
_use_batch_api: bool | None = None  # resolved on first call; reset on API failure


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed all texts. Auto-detects batch vs legacy API on first call.
    If the selected API fails, the cache is cleared so the next call re-probes.
    """
    global _use_batch_api
    if not texts:
        return []

    async with httpx.AsyncClient(timeout=300) as client:
        if _use_batch_api is None:
            _use_batch_api = await _probe_batch_api(client)
            logger.info("Ollama embedding API: %s", "batch /api/embed" if _use_batch_api else "legacy /api/embeddings")

        try:
            if _use_batch_api:
                return await _embed_batch_api(client, texts)
            else:
                return await _embed_legacy_api(client, texts)
        except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
            # If the call itself fails, clear the cache so next attempt re-probes.
            # This handles the case where Ollama was starting up when the probe ran.
            logger.warning("Embedding call failed (%s) — resetting API probe cache", exc)
            _use_batch_api = None
            raise


async def _probe_batch_api(client: httpx.AsyncClient) -> bool:
    """Return True if /api/embed is available and working.
    Retries up to MAX_PROBE_ATTEMPTS times with backoff to handle the case
    where the worker starts before Ollama's HTTP server is fully ready.
    """
    MAX_PROBE_ATTEMPTS = 12   # up to ~60 s of waiting
    PROBE_BACKOFF     = 5     # seconds between attempts

    for attempt in range(MAX_PROBE_ATTEMPTS):
        try:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": ["test"]},
                timeout=15,
            )
            if resp.status_code == 200:
                return True
            body = resp.text
            logger.warning("/api/embed returned %d: %s", resp.status_code, body[:200])
            # "model not found" → fail immediately with a clear message
            if "not found" in body and "pulling" in body:
                raise RuntimeError(
                    f"Ollama model '{settings.ollama_embed_model}' is not pulled. "
                    f"Run: docker compose exec ollama ollama pull {settings.ollama_embed_model}"
                )
            # 404 without "not found" → Ollama is still starting up, try legacy
            legacy = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": "test"},
                timeout=15,
            )
            if legacy.status_code == 200:
                return False   # legacy works → old Ollama, no batch API
            logger.warning("/api/embeddings returned %d: %s", legacy.status_code, legacy.text[:200])
            # Both non-200 → still starting up, wait and retry
            logger.warning(
                "Ollama not ready yet (attempt %d/%d) — waiting %ds",
                attempt + 1, MAX_PROBE_ATTEMPTS, PROBE_BACKOFF,
            )
        except Exception as exc:
            logger.warning(
                "Ollama probe error (attempt %d/%d): %s — waiting %ds",
                attempt + 1, MAX_PROBE_ATTEMPTS, exc, PROBE_BACKOFF,
            )
        await asyncio.sleep(PROBE_BACKOFF)

    raise RuntimeError(
        f"Ollama at {settings.ollama_base_url} did not become ready after "
        f"{MAX_PROBE_ATTEMPTS * PROBE_BACKOFF}s. Is the model pulled?"
    )


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
