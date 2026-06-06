"""
Ollama worker provider — wraps the existing ollama_embedder logic
plus adds a non-streaming generate() for summarization strategies.
"""
import asyncio
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Re-use the existing batch embedding logic from ollama_embedder
from embedding.ollama_embedder import embed_batch as _ollama_embed_batch


class OllamaWorkerProvider:
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await _ollama_embed_batch(texts)

    async def generate(self, prompt: str) -> str:
        """Non-streaming generation via Ollama /api/generate."""
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": settings.ollama_temperature,
                        "num_ctx": settings.ollama_num_ctx,
                    },
                },
            )
            resp.raise_for_status()
            return resp.json()["response"].strip()
