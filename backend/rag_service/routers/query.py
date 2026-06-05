import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chains import rag_chain
from services import context_builder, llm_client, retriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    user_id: str
    document_ids: Optional[list[str]] = None
    conversation_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    user_id: str
    document_ids: Optional[list[str]] = None
    top_k: int = 5


@router.post("/query")
async def query(request: QueryRequest):
    """Stream RAG answer as SSE."""
    return StreamingResponse(
        rag_chain.run(
            query=request.query,
            user_id=request.user_id,
            document_ids=request.document_ids,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/search")
async def search(request: SearchRequest):
    """Semantic search without LLM generation."""
    query_embedding = await llm_client.embed(request.query)
    chunks = retriever.retrieve(
        query_embedding=query_embedding,
        user_id=request.user_id,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )
    return {
        "query": request.query,
        "results": [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "text": c.text,
                "score": round(c.score, 4),
                "page_number": c.page_number,
                "filename": "",  # fetched from PostgreSQL in api_gateway if needed
            }
            for c in chunks
        ],
    }
