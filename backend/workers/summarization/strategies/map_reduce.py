"""
Map-Reduce summarization for large documents (> 8k tokens).
1. Map: summarize each chunk concurrently (Semaphore limits Ollama load)
2. Reduce: summarize all chunk summaries into a final summary
"""
import asyncio

import httpx

from config import get_settings

settings = get_settings()

# Max concurrent LLM calls during map phase — lower than embedding (heavier inference)
CONCURRENCY = 4
# Sample at most this many chunks evenly from the document — keeps LLM calls bounded
MAX_MAP_CHUNKS = 30

CHUNK_PROMPT = """Summarize the following text segment in 2-3 sentences:

{text}

Summary:"""

REDUCE_PROMPT = """You have been given multiple summaries of sections from a document.
Combine them into a single coherent summary of the entire document in 5-8 sentences.

Section summaries:
{summaries}

Final document summary:"""


async def _summarize_chunk(client: httpx.AsyncClient, text: str) -> str:
    resp = await client.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_llm_model,
            "prompt": CHUNK_PROMPT.format(text=text[:3000]),
            "stream": False,
            "options": {"temperature": settings.ollama_temperature},
        },
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


async def summarize(chunks: list[str]) -> str:
    # Sample evenly so LLM calls stay bounded regardless of document length
    if len(chunks) > MAX_MAP_CHUNKS:
        step = len(chunks) / MAX_MAP_CHUNKS
        chunks = [chunks[int(i * step)] for i in range(MAX_MAP_CHUNKS)]

    sem = asyncio.Semaphore(CONCURRENCY)

    async def _bounded(chunk_text: str) -> str:
        async with sem:
            return await _summarize_chunk(client, chunk_text)

    async with httpx.AsyncClient(timeout=600) as client:
        chunk_summaries = await asyncio.gather(*[_bounded(c) for c in chunks])

        combined = "\n\n".join(f"- {s}" for s in chunk_summaries)
        resp = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_llm_model,
                "prompt": REDUCE_PROMPT.format(summaries=combined[:8000]),
                "stream": False,
                "options": {"temperature": settings.ollama_temperature},
            },
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
