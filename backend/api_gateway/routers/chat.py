import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from config import get_settings
from dependencies import get_current_user
from models.user import User
from schemas.chat import ChatRequest, SearchRequest, SearchResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["chat"])


async def _stream_rag_response(
    query: str,
    user_id: str,
    document_ids: list[str] | None,
    conversation_id: str | None,
) -> AsyncGenerator[bytes, None]:
    payload = {
        "query": query,
        "user_id": user_id,
        "document_ids": [str(d) for d in document_ids] if document_ids else None,
        "conversation_id": conversation_id,
    }
    client = httpx.AsyncClient(timeout=300)
    try:
        async with client.stream("POST", f"{settings.rag_service_url}/query", json=payload) as resp:
            if resp.status_code != 200:
                yield b"data: [ERROR] RAG service unavailable\n\n"
                return
            async for chunk in resp.aiter_bytes():
                yield chunk
    except (httpx.RemoteProtocolError, httpx.ReadTimeout) as exc:
        logger.warning("RAG stream ended early: %s", exc)
    finally:
        await client.aclose()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Stream chat response via SSE."""
    return StreamingResponse(
        _stream_rag_response(
            query=request.query,
            user_id=str(current_user.id),
            document_ids=request.document_ids,
            conversation_id=request.conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
):
    """Semantic search — proxies to RAG service."""
    payload = {
        "query": request.query,
        "user_id": str(current_user.id),
        "document_ids": [str(d) for d in request.document_ids] if request.document_ids else None,
        "top_k": request.top_k,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{settings.rag_service_url}/search", json=payload)
            resp.raise_for_status()
            return SearchResponse(**resp.json())
        except httpx.HTTPError as exc:
            logger.error("RAG service search failed: %s", exc)
            raise HTTPException(status_code=503, detail="Search service unavailable")
