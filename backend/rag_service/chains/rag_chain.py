"""
Core RAG chain:
  embed query → retrieve chunks → build context → format prompt → stream LLM
"""
import json
from typing import AsyncGenerator, Optional

from config import get_settings
from services import context_builder, llm_client, retriever
from utils.prompt_templates import QA_PROMPT

settings = get_settings()


async def run(
    query: str,
    user_id: str,
    document_ids: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline — yields SSE-formatted tokens.
    """
    # 1. Embed the query
    query_embedding = await llm_client.embed(query)

    # 2. Retrieve top-k chunks from ChromaDB
    chunks = retriever.retrieve(
        query_embedding=query_embedding,
        user_id=user_id,
        document_ids=document_ids,
        top_k=settings.rag_top_k_retrieve,
    )

    # 3. Rerank: drop low-confidence chunks, then take top-k
    MIN_SCORE = 0.50
    relevant_chunks = [c for c in chunks if c.score >= MIN_SCORE]
    top_chunks = relevant_chunks[: settings.rag_top_k_rerank]

    # 4. Build context string within token budget
    context_str, sources = context_builder.build_context(top_chunks)

    if not context_str:
        yield "data: " + json.dumps({"token": "No relevant documents found for your query.", "sources": [], "done": False}) + "\n\n"
        yield "data: " + json.dumps({"token": "", "sources": [], "done": True}) + "\n\n"
        return

    # 5. Format prompt
    prompt = QA_PROMPT.format(context=context_str, question=query)

    # 6. Stream LLM response
    async for token in llm_client.generate_stream(prompt):
        yield "data: " + json.dumps({"token": token, "sources": [], "done": False}) + "\n\n"

    # 7. Send final SSE event with sources
    yield "data: " + json.dumps({"token": "", "sources": sources, "done": True}) + "\n\n"
