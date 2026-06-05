"""
Embedding generation via Ollama /api/embeddings endpoint.
"""
import httpx

from config import get_settings

settings = get_settings()
BATCH_SIZE = 32


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns list of float vectors."""
    embeddings: list[list[float]] = []
    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            results = []
            for text in batch:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": settings.ollama_embed_model, "prompt": text},
                )
                resp.raise_for_status()
                results.append(resp.json()["embedding"])
            embeddings.extend(results)
    return embeddings
