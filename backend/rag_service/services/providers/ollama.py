"""
Ollama LLM + embedding provider.
Extracted verbatim from the original llm_client.py — no behaviour changes.
"""
import json
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaProvider:
    async def embed(self, text: str) -> list[float]:
        """Single-text embedding via Ollama /api/embeddings."""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    async def generate_stream(self, prompt: str):
        """Stream tokens from Ollama /api/generate."""
        payload = {
            "model": settings.ollama_llm_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": settings.ollama_temperature,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": settings.ollama_num_predict,
            },
        }
        client = httpx.AsyncClient(timeout=300)
        try:
            async with client.stream(
                "POST", f"{settings.ollama_base_url}/api/generate", json=payload
            ) as resp:
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
        finally:
            await client.aclose()

    async def generate(self, prompt: str) -> str:
        """Non-streaming generation — returns full response string."""
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
