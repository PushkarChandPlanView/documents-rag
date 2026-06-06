from datetime import datetime
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


class DocumentSearchRequest(BaseModel):
    query: str
    document_ids: Optional[list[UUID]] = None
    top_k: int = 10


class DocumentSearchResult(BaseModel):
    document_id: UUID
    document_name: str
    file_type: str
    score: float
    snippet: str
    page_number: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    status: Optional[str] = None
    description: Optional[str] = None
    file_size_bytes: Optional[int] = None


class DocumentSearchResponse(BaseModel):
    query: str
    results: list[DocumentSearchResult]
