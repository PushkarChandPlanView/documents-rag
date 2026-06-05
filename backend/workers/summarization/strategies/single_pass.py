"""Single-pass summarization for documents ≤ 8k tokens."""
import httpx

from config import get_settings

settings = get_settings()

SUMMARIZE_PROMPT = """You are a document summarization assistant.
Provide a clear, concise summary of the following document text.
Focus on the main topics, key findings, and important details.
Keep the summary between 3-8 sentences.

Document:
{text}

Summary:"""


async def summarize(text: str) -> str:
    prompt = SUMMARIZE_PROMPT.format(text=text[:12000])  # safety truncation
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
