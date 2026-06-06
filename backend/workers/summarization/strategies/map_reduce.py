"""
Map-Reduce summarization for large documents (> TOKEN_THRESHOLD tokens).
1. Map: summarize each chunk concurrently (Semaphore limits LLM load)
2. Reduce: summarize all chunk summaries into a final summary
"""
import asyncio

from shared.providers import llm_factory

# Max concurrent LLM calls during map phase
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


async def _summarize_chunk(text: str) -> str:
    return await llm_factory.generate(CHUNK_PROMPT.format(text=text[:3000]))


async def summarize(chunks: list[str]) -> str:
    # Sample evenly so LLM calls stay bounded regardless of document length
    if len(chunks) > MAX_MAP_CHUNKS:
        step = len(chunks) / MAX_MAP_CHUNKS
        chunks = [chunks[int(i * step)] for i in range(MAX_MAP_CHUNKS)]

    sem = asyncio.Semaphore(CONCURRENCY)

    async def _bounded(chunk_text: str) -> str:
        async with sem:
            return await _summarize_chunk(chunk_text)

    chunk_summaries = await asyncio.gather(*[_bounded(c) for c in chunks])
    combined = "\n\n".join(f"- {s}" for s in chunk_summaries)
    return await llm_factory.generate(REDUCE_PROMPT.format(summaries=combined[:8000]))
