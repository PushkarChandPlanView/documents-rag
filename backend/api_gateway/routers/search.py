import logging
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.user import User
from schemas.chat import DocumentSearchRequest, DocumentSearchResponse, DocumentSearchResult
from services.document_service import get_documents_by_ids

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["search"])


@router.post("/search/documents", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Document-level semantic search. Returns one result per document, ranked by relevance."""
    rag_payload = {
        "query": request.query,
        "user_id": str(current_user.id),
        "document_ids": [str(d) for d in request.document_ids] if request.document_ids else None,
        "top_k": settings.rag_search_top_k,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{settings.rag_service_url}/search", json=rag_payload)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("RAG document-search failed: %s", exc)
            raise HTTPException(status_code=503, detail="Search service unavailable")

    chunks: list[dict] = resp.json().get("results", [])

    # Group by document_id, keep highest-score chunk per doc
    best: dict[str, dict] = {}
    for chunk in chunks:
        doc_id = str(chunk["document_id"])
        if doc_id not in best or chunk["score"] > best[doc_id]["score"]:
            best[doc_id] = chunk

    # Rank then trim to top_k before the DB round-trip
    ranked_ids = sorted(best, key=lambda d: best[d]["score"], reverse=True)[: request.top_k]

    db_docs = await get_documents_by_ids(db, [UUID(d) for d in ranked_ids], current_user.id)

    results: list[DocumentSearchResult] = []
    for doc_id in ranked_ids:
        chunk = best[doc_id]
        db_doc = db_docs.get(UUID(doc_id))
        if db_doc is None:
            continue  # not owned by this user or already deleted

        text = chunk["text"]
        snippet = text[:200].rstrip() + ("…" if len(text) > 200 else "")

        results.append(DocumentSearchResult(
            document_id=db_doc.id,
            document_name=db_doc.name,
            file_type=os.path.splitext(db_doc.name)[1].lstrip(".").lower() or db_doc.mime_type or "",
            score=round(chunk["score"], 4),
            snippet=snippet,
            page_number=chunk.get("page_number"),
            created_at=db_doc.created_at,
            updated_at=db_doc.updated_at,
            status=db_doc.status,
            description=db_doc.description,
            file_size_bytes=db_doc.file_size_bytes,
        ))

    return DocumentSearchResponse(query=request.query, results=results)
