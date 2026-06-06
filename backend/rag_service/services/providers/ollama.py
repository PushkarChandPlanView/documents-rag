"""
Ollama LLM + embedding provider.
"""
import json
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Split the combined prompt string into (system, user) parts.
# The prompt templates are written as:
#   /no_think
#   <system instruction>
#   ...
#   <user content (context + question)>
#
# We use /api/chat so Ollama applies the model's chat template correctly,
# which is the only way qwen3's /no_think token is honoured.
_SYSTEM_MARKER = "/no_think\n"


def _split_prompt(prompt: str) -> tuple[str, str]:
    """Return (system_content, user_content) from a combined prompt string."""
    if prompt.startswith(_SYSTEM_MARKER):
        prompt = prompt[len(_SYSTEM_MARKER):]
    # Everything before the first blank line is the system block;
    # the rest (context + question) is the user message.
    parts = prompt.split("\n\n", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "", prompt.strip()


def _chat_payload(prompt: str, stream: bool) -> dict:
    system, user = _split_prompt(prompt)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    # /no_think prefix on the user turn tells qwen3 to skip thinking mode
    messages.append({"role": "user", "content": f"/no_think\n{user}"})
    return {
        "model": settings.ollama_llm_model,
        "messages": messages,
        "stream": stream,
        "think": False,
        "options": {
            "temperature": settings.ollama_temperature,
            "num_ctx": settings.ollama_num_ctx,
        },
    }


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
        """Stream tokens from Ollama /api/chat. Thinking content is passed
        through as-is; the frontend splits on </think> and renders it
        separately."""
        payload = {**_chat_payload(prompt, stream=True), "options": {
            "temperature": settings.ollama_temperature,
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": settings.ollama_num_predict,
        }}
        client = httpx.AsyncClient(timeout=300)
        try:
            async with client.stream(
                "POST", f"{settings.ollama_base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
        finally:
            await client.aclose()

    async def generate(self, prompt: str) -> str:
        """Non-streaming generation via Ollama /api/chat."""
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=_chat_payload(prompt, stream=False),
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
            if "</think>" in content:
                content = content.split("</think>", 1)[1]
            return content.strip()
