"""
Async Ollama LLM client.
Supports both streaming and non-streaming generation.
"""
import json
from typing import AsyncGenerator

import httpx

from config import get_settings

settings = get_settings()


async def generate_stream(prompt: str) -> AsyncGenerator[str, None]:
    """Stream tokens from Ollama /api/generate."""
    payload = {
        "model": settings.ollama_llm_model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": settings.ollama_temperature,
            "num_ctx": settings.ollama_num_ctx,
        },
    }
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("POST", f"{settings.ollama_base_url}/api/generate", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue


async def embed(text: str) -> list[float]:
    """Generate embedding vector for a single text."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
