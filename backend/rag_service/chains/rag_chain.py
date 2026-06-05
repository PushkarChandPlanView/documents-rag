"""
Core RAG chain:
  embed query → retrieve chunks → build context → format prompt → stream LLM
"""
import json
import logging
from typing import AsyncGenerator, Optional

from config import get_settings
from services import context_builder, llm_client, retriever
from utils.prompt_templates import QA_PROMPT

settings = get_settings()
logger = logging.getLogger(__name__)


async def run(
    query: str,
    user_id: str,
    document_ids: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline — yields SSE-formatted tokens.
    """
    def _status(msg: str) -> str:
        return "data: " + json.dumps({"type": "status", "message": msg, "token": "", "sources": [], "done": False}) + "\n\n"

    # 1. Embed the query
    yield _status("Searching documents…")
    query_embedding = await llm_client.embed(query)

    # 2. Retrieve top-k chunks from pgvector
    chunks = await retriever.retrieve(
        query_embedding=query_embedding,
        user_id=user_id,
        document_ids=document_ids,
        top_k=settings.rag_top_k_retrieve,
        query=query,
    )

    # 3. Rerank: drop low-confidence chunks, then take top-k
    logger.info(
        "Retrieved %d chunks for query=%r scores=%s",
        len(chunks),
        query,
        [round(c.score, 3) for c in chunks],
    )
    relevant_chunks = [c for c in chunks if c.score >= settings.rag_min_score]
    logger.info(
        "%d/%d chunks passed min_score=%.2f — all scores: %s",
        len(relevant_chunks),
        len(chunks),
        settings.rag_min_score,
        [round(c.score, 3) for c in chunks],
    )
    top_chunks = relevant_chunks[: settings.rag_top_k_rerank]

    # 4. Build context string within token budget
    context_str, sources = context_builder.build_context(top_chunks)

    if not context_str:
        yield "data: " + json.dumps({"token": "No relevant documents found for your query.", "sources": [], "done": False}) + "\n\n"
        yield "data: " + json.dumps({"token": "", "sources": [], "done": True}) + "\n\n"
        return

    # 5. Format prompt
    yield _status("Generating answer…")
    prompt = QA_PROMPT.format(context=context_str, question=query)

    # 6. Stream LLM response
    first_token = True
    async for token in llm_client.generate_stream(prompt):
        if first_token:
            first_token = False
        yield "data: " + json.dumps({"type": "token", "token": token, "sources": [], "done": False}) + "\n\n"

    # 7. Send final SSE event with sources
    yield "data: " + json.dumps({"type": "token", "token": "", "sources": sources, "done": True}) + "\n\n"
