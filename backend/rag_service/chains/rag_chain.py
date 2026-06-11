"""
Core RAG chain:
  embed query → retrieve chunks from Elasticsearch → build context → stream LLM
"""
import json
import logging
from typing import AsyncGenerator, Optional

from config import get_settings
from services import context_builder, llm_client, es_retriever
from services.retriever import RetrievedChunk
from utils.prompt_templates import QA_PROMPT

settings = get_settings()
logger = logging.getLogger(__name__)


def _es_to_retrieved(c) -> RetrievedChunk:
    """Convert an ESChunk to the RetrievedChunk dataclass context_builder expects."""
    return RetrievedChunk(
        chunk_id=c.chunk_id,
        document_id=c.document_id,
        text=c.text,
        score=c.score,
        chunk_index=getattr(c, "chunk_index", 0),
        page_number=c.page_number,
        user_id=getattr(c, "user_id", ""),
        document_name=c.document_name,
        file_type=getattr(c, "file_type", ""),
    )


async def run(
    query: str,
    user_id: str,
    document_ids: Optional[list[str]] = None,
    source_types: Optional[list[str]] = None,
    file_types: Optional[list[str]] = None,
    folder_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline — yields SSE-formatted tokens.
    Retrieves from Elasticsearch (hybrid BM25 + vector search).
    """
    def _status(msg: str) -> str:
        return "data: " + json.dumps({"type": "status", "message": msg, "token": "", "sources": [], "done": False}) + "\n\n"

    # 1. Embed the query
    yield _status("Searching documents…")
    query_embedding = await llm_client.embed(query)

    # 2. Retrieve top-k chunks from Elasticsearch (hybrid search)
    try:
        es_chunks = await es_retriever.hybrid_search(
            query_text=query,
            query_vector=query_embedding,
            user_id=user_id,
            document_ids=document_ids,
            top_k=settings.rag_top_k_retrieve,
            source_types=source_types,
            file_types=file_types,
            folder_id=folder_id,
        )
    except Exception as exc:
        logger.error("ES hybrid search failed: %s", exc, exc_info=True)
        es_chunks = []

    chunks = [_es_to_retrieved(c) for c in es_chunks]

    logger.info(
        "Retrieved %d chunks from ES for query=%r scores=%s",
        len(chunks), query, [round(c.score, 3) for c in chunks],
    )

    top_chunks = chunks[: settings.rag_top_k_rerank]

    # 3. Build context string within token budget
    context_str, sources = context_builder.build_context(top_chunks)

    if not context_str:
        yield "data: " + json.dumps({"token": "No relevant documents found for your query.", "sources": [], "done": False}) + "\n\n"
        yield "data: " + json.dumps({"token": "", "sources": [], "done": True}) + "\n\n"
        return

    # 4. Format prompt
    yield _status("Generating answer…")
    prompt = QA_PROMPT.format(context=context_str, question=query)

    # 5. Stream LLM response
    try:
        async for token in llm_client.generate_stream(prompt):
            yield "data: " + json.dumps({"type": "token", "token": token, "sources": [], "done": False}) + "\n\n"
    except Exception as exc:
        logger.warning("LLM generation failed (%s) — returning top chunks as fallback", exc)
        snippets = [f"**{c.document_name}**: {c.text[:400]}" for c in top_chunks[:3]]
        fallback = "⚠️ LLM unavailable. Top retrieved passages:\n\n" + "\n\n".join(snippets)
        yield "data: " + json.dumps({"type": "token", "token": fallback, "sources": [], "done": False}) + "\n\n"

    # 6. Send final SSE event with sources
    yield "data: " + json.dumps({"type": "token", "token": "", "sources": sources, "done": True}) + "\n\n"
