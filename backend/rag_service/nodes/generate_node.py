"""
Generate node — assembles final answer from retrieved chunks using Claude Sonnet.
Deduplicates chunks, caps context at 14 000 chars, yields SSE tokens.
"""
import logging
from typing import TYPE_CHECKING, AsyncGenerator

from services import llm_client

if TYPE_CHECKING:
    from chains.agentic_chain import AgenticState

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS  = 2_000   # per chunk
_MAX_CONTEXT_CHARS  = 14_000  # total context budget

_SYSTEM_PROMPT = """\
You are a helpful enterprise AI assistant. Answer the user's question using ONLY
the document chunks provided below. Cite every factual claim with the chunk ID
in square brackets, e.g. [chunk-abc123]. If the context is insufficient, say so
explicitly rather than making up information. Be concise and structured."""


def _build_context(chunks: list[dict]) -> tuple[str, list[dict]]:
    """Deduplicate by chunk_id, truncate, and cap total chars."""
    seen: set[str] = set()
    unique: list[dict] = []
    for c in chunks:
        cid = c.get("chunk_id") or c.get("id", "")
        if cid and cid in seen:
            continue
        seen.add(cid)
        unique.append(c)

    parts: list[str] = []
    total = 0
    sources: list[dict] = []
    for c in unique:
        text    = (c.get("text") or "")[:_MAX_CONTENT_CHARS]
        cid     = c.get("chunk_id") or c.get("id", "unknown")
        name    = c.get("document_name", "unknown")
        snippet = f"[{cid}] ({name})\n{text}"
        if total + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        parts.append(snippet)
        total += len(snippet)
        sources.append({
            "chunk_id":     cid,
            "document_id":  c.get("document_id", ""),
            "document_name": name,
            "score":        round(c.get("score", 0.0), 4),
        })

    return "\n\n---\n\n".join(parts), sources


async def generate_node(state: "AgenticState") -> dict:
    query  = state.get("refined_query") or state["query"]
    chunks = state.get("retrieved_chunks", [])

    context, sources = _build_context(chunks)

    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"=== DOCUMENT CHUNKS ===\n{context}\n\n"
        f"=== QUESTION ===\n{query}"
    )

    logger.info("Generate: chunks=%d context_chars=%d", len(chunks), len(context))

    # Collect streamed tokens into full answer (caller handles SSE streaming)
    tokens: list[str] = []
    try:
        async for token in llm_client.generate_stream(prompt):
            tokens.append(token)
        answer = "".join(tokens).strip()
    except Exception as exc:
        logger.error("Generate: LLM call failed (%s) — returning context summary", exc)
        # Graceful degradation: return a snippet of top chunks as the answer
        snippets = []
        for c in (chunks or [])[:3]:
            name = c.get("document_name", "document")
            text = (c.get("text") or "")[:400]
            snippets.append(f"**{name}**: {text}")
        answer = (
            "⚠️ LLM generation failed (model unavailable). "
            "Here are the top retrieved passages:\n\n"
            + "\n\n".join(snippets)
        ) if snippets else "⚠️ LLM generation failed and no chunks were retrieved."

    return {"answer": answer, "_sources": sources}
