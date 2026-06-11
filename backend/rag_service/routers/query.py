import json
import logging
from typing import AsyncGenerator, Literal, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chains import rag_chain
from chains.agentic_chain import run_agentic_search
from services import context_builder, llm_client, retriever
from services import es_retriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])

SearchMode = Literal["hybrid", "semantic", "keyword", "pgvector"]


class QueryRequest(BaseModel):
    query: str
    user_id: str
    document_ids: Optional[list[str]] = None
    conversation_id: Optional[str] = None
    source_types: Optional[list[str]] = None
    file_types: Optional[list[str]] = None
    folder_id: Optional[str] = None


class AgenticQueryRequest(BaseModel):
    query: str
    user_id: str
    document_ids: Optional[list[str]] = None
    max_iter: int = 3
    source_types: Optional[list[str]] = None
    file_types: Optional[list[str]] = None
    folder_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    user_id: str
    document_ids: Optional[list[str]] = None
    top_k: int = 5
    mode: SearchMode = "hybrid"  # hybrid | semantic | keyword | pgvector
    source_types: Optional[list[str]] = None
    file_types: Optional[list[str]] = None
    folder_id: Optional[str] = None


async def _safe_stream(request: QueryRequest) -> AsyncGenerator[str, None]:
    """Wrap rag_chain.run() so any mid-stream exception is sent as a final SSE
    error event rather than dropping the connection (which causes an
    'incomplete chunked read' on the api_gateway side)."""
    try:
        async for chunk in rag_chain.run(
            query=request.query,
            user_id=request.user_id,
            document_ids=request.document_ids,
            source_types=request.source_types,
            file_types=request.file_types,
            folder_id=request.folder_id,
        ):
            yield chunk
    except Exception as exc:
        logger.error("RAG chain error during streaming: %s", exc, exc_info=True)
        yield (
            "data: "
            + json.dumps({
                "type": "error",
                "token": "Sorry, an error occurred while generating the answer.",
                "sources": [],
                "done": True,
            })
            + "\n\n"
        )


@router.post("/query")
async def query(request: QueryRequest):
    """Stream RAG answer as SSE."""
    return StreamingResponse(
        _safe_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _safe_stream_agentic(request: AgenticQueryRequest) -> AsyncGenerator[str, None]:
    """Wrap run_agentic_search so any mid-stream exception surfaces as an SSE error."""
    import json as _json
    try:
        async for chunk in run_agentic_search(
            query=request.query,
            user_id=request.user_id,
            document_ids=request.document_ids,
            max_iter=request.max_iter,
            source_types=request.source_types,
            file_types=request.file_types,
            folder_id=request.folder_id,
        ):
            yield chunk
    except Exception as exc:
        logger.error("Agentic stream error: %s", exc, exc_info=True)
        yield (
            "data: "
            + _json.dumps({"type": "error", "content": "Agentic search failed.", "sources": [], "done": True})
            + "\n\n"
        )


@router.post("/agentic-query")
async def agentic_query(request: AgenticQueryRequest):
    """Stream agentic RAG answer as SSE (router → search → reflect → generate loop)."""
    return StreamingResponse(
        _safe_stream_agentic(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/search")
async def search(request: SearchRequest):
    """
    Search document chunks without LLM generation.

    Modes:
      hybrid   — BM25 + kNN fused with RRF via Elasticsearch (default)
      semantic — pure kNN via Elasticsearch
      keyword  — pure BM25 via Elasticsearch
      pgvector — original pgvector hybrid scoring (fallback / no ES required)
    """
    if request.mode == "pgvector":
        # Original pgvector path — always available as fallback
        query_embedding = await llm_client.embed(request.query)
        chunks = await retriever.retrieve(
            query_embedding=query_embedding,
            user_id=request.user_id,
            document_ids=request.document_ids,
            top_k=request.top_k,
            query=request.query,
        )
        return {
            "query": request.query,
            "mode": "pgvector",
            "results": [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "text": c.text,
                    "score": round(c.score, 4),
                    "page_number": c.page_number,
                    "document_name": c.document_name,
                    "file_type": c.file_type,
                }
                for c in chunks
            ],
        }

    # Elasticsearch paths
    if request.mode == "keyword":
        es_chunks = await es_retriever.keyword_search(
            query_text=request.query,
            user_id=request.user_id,
            document_ids=request.document_ids,
            top_k=request.top_k,
            source_types=request.source_types,
            file_types=request.file_types,
            folder_id=request.folder_id,
        )
    else:
        # hybrid (default) or semantic both need an embedding
        query_embedding = await llm_client.embed(request.query)
        if request.mode == "semantic":
            es_chunks = await es_retriever.semantic_search(
                query_vector=query_embedding,
                user_id=request.user_id,
                document_ids=request.document_ids,
                top_k=request.top_k,
                source_types=request.source_types,
                file_types=request.file_types,
                folder_id=request.folder_id,
            )
        else:
            es_chunks = await es_retriever.hybrid_search(
                query_text=request.query,
                query_vector=query_embedding,
                user_id=request.user_id,
                document_ids=request.document_ids,
                top_k=request.top_k,
                source_types=request.source_types,
                file_types=request.file_types,
                folder_id=request.folder_id,
            )

    return {
        "query": request.query,
        "mode": request.mode,
        "results": [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "text": c.text,
                "score": round(c.score, 4),
                "page_number": c.page_number,
                "document_name": c.document_name,
                "file_type": c.file_type,
                "latency_ms": c.latency_ms,
            }
            for c in es_chunks
        ],
    }
