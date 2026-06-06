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
import tiktoken

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BATCH_SIZE = 32
CONCURRENCY = 4   # concurrent batch requests
_use_batch_api: bool | None = None  # resolved on first call; reset on API failure

# mxbai-embed-large (and similar BERT-style models) has a 512-token context.
# BERT tokenizers produce ~1.8× more tokens than cl100k_base for the same text,
# so we cap at embed_chunk_max_tokens (240 cl100k) which gives ~450 BERT tokens,
# leaving room for Ollama's overhead and the document-name prefix.
# This also prevents 400 errors from Ollama versions that ignore truncate:true.
_MAX_TOKENS = settings.embed_chunk_max_tokens
_enc = tiktoken.get_encoding("cl100k_base")


def _truncate(text: str) -> str:
    tokens = _enc.encode(text)
    if len(tokens) <= _MAX_TOKENS:
        return text
    truncated = _enc.decode(tokens[:_MAX_TOKENS])
    logger.warning("Truncated text from %d to %d cl100k tokens before embedding", len(tokens), _MAX_TOKENS)
    return truncated


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed all texts. Auto-detects batch vs legacy API on first call.
    If the selected API fails, the cache is cleared so the next call re-probes.
    """
    global _use_batch_api
    if not texts:
        return []

    texts = [_truncate(t) for t in texts]

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
    # Filter empty/whitespace texts — Ollama's /api/embed returns 400 on empty strings.
    # Keep original indices so we can reconstruct the full result list afterwards.
    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    if not indexed:
        return [[] for _ in texts]

    non_empty_indices, non_empty_texts = zip(*indexed)

    batches = [
        non_empty_texts[i:i + BATCH_SIZE]
        for i in range(0, len(non_empty_texts), BATCH_SIZE)
    ]
    batch_starts = [
        non_empty_indices[i]
        for i in range(0, len(non_empty_indices), BATCH_SIZE)
    ]
    completed = 0
    sem = asyncio.Semaphore(CONCURRENCY)

    async def _one_batch(batch: tuple[str, ...]) -> list[list[float]]:
        nonlocal completed
        async with sem:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={
                    "model": settings.ollama_embed_model,
                    "input": list(batch),
                    "truncate": True,
                },
            )
            if not resp.is_success:
                logger.error(
                    "/api/embed returned %d for batch of %d texts: %s",
                    resp.status_code, len(batch), resp.text[:400],
                )
            resp.raise_for_status()
            completed += len(batch)
            pct = int(completed / len(non_empty_texts) * 100)
            logger.info("Embedding progress: %d/%d chunks (%d%%)", completed, len(non_empty_texts), pct)
            return resp.json()["embeddings"]

    batch_results = await asyncio.gather(*[_one_batch(b) for b in batches])
    flat_vecs = [vec for batch in batch_results for vec in batch]

    # Reconstruct full-length list, leaving zero vectors for filtered positions
    dim = len(flat_vecs[0]) if flat_vecs else 0
    output: list[list[float]] = [[0.0] * dim for _ in texts]
    for out_idx, vec in zip(non_empty_indices, flat_vecs):
        output[out_idx] = vec
    return output


async def _embed_legacy_api(client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    if not indexed:
        return [[] for _ in texts]

    completed = 0
    sem = asyncio.Semaphore(8)

    async def _one(orig_idx: int, text: str) -> tuple[int, list[float]]:
        nonlocal completed
        async with sem:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": text},
            )
            if not resp.is_success:
                logger.error(
                    "/api/embeddings returned %d for text[%d]: %s",
                    resp.status_code, orig_idx, resp.text[:400],
                )
            resp.raise_for_status()
            completed += 1
            pct = int(completed / len(indexed) * 100)
            logger.info("Embedding progress: %d/%d chunks (%d%%)", completed, len(indexed), pct)
            return orig_idx, resp.json()["embedding"]

    pairs = await asyncio.gather(*[_one(i, t) for i, t in indexed])
    pairs_sorted = sorted(pairs, key=lambda x: x[0])

    dim = len(pairs_sorted[0][1]) if pairs_sorted else 0
    output: list[list[float]] = [[0.0] * dim for _ in texts]
    for orig_idx, vec in pairs_sorted:
        output[orig_idx] = vec
    return output
