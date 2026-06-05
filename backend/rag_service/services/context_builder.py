"""
Assembles retrieved chunks into a structured prompt context
within a token budget.
"""
import tiktoken

from config import get_settings
from .retriever import RetrievedChunk

settings = get_settings()


def _count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def build_context(chunks: list[RetrievedChunk], token_budget: int | None = None) -> tuple[str, list[dict]]:
    """
    Returns:
        context_str: formatted context string to inject into prompt
        sources: list of source metadata dicts for citations
    """
    budget = token_budget or settings.rag_context_token_budget
    context_parts: list[str] = []
    sources: list[dict] = []
    used_tokens = 0

    for chunk in chunks:
        page_info = f" (page {chunk.page_number})" if chunk.page_number else ""
        header = f"[Source: document_id={chunk.document_id}{page_info}]"
        chunk_text = f"{header}\n{chunk.text}"
        chunk_tokens = _count_tokens(chunk_text)

        if used_tokens + chunk_tokens > budget:
            break

        context_parts.append(chunk_text)
        used_tokens += chunk_tokens
        sources.append({
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "page_number": chunk.page_number,
            "score": round(chunk.score, 4),
        })

    context_str = "\n\n---\n\n".join(context_parts)
    return context_str, sources
