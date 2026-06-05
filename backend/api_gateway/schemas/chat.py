from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    document_ids: Optional[list[UUID]] = None  # None = search all user's docs
    conversation_id: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    document_ids: Optional[list[UUID]] = None
    top_k: int = 5


class SearchResult(BaseModel):
    chunk_id: str
    document_id: UUID
    filename: str
    text: str
    score: float
    page_number: Optional[int] = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
