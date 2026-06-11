"""
Pydantic schemas for the comment API.

Design decisions:
- `CommentCreate` is the only schema that includes `document_id` — updates only
  touch `content`, and the service layer owns the document/parent validation.
- `content_not_blank` strips whitespace before saving so "   " is rejected.
- `CommentResponse` is fully recursive via `model_rebuild()` to support nested replies.
- `PaginatedComments` wraps the list response so callers always get consistent
  pagination metadata regardless of page size.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Nested author summary ──────────────────────────────────────────────────────

class CommentAuthor(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Request schemas ────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    document_id: str
    content: str = Field(..., min_length=1, max_length=10_000)
    parent_id: Optional[str] = None

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Content cannot be blank or whitespace only")
        return stripped


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10_000)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Content cannot be blank or whitespace only")
        return stripped


# ── Response schemas ───────────────────────────────────────────────────────────

class CommentResponse(BaseModel):
    id: str
    document_id: str
    parent_id: Optional[str]
    content: str
    author: CommentAuthor
    created_at: datetime
    updated_at: datetime
    like_count: int = 0
    liked_by_me: bool = False
    # Replies are included inline; clients can render full threads without extra calls
    replies: List["CommentResponse"] = []

    model_config = {"from_attributes": True}


# Required for self-referencing model
CommentResponse.model_rebuild()


class PaginatedComments(BaseModel):
    items: List[CommentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── Example API responses (for documentation / contract tests) ─────────────────

EXAMPLE_COMMENT_RESPONSE = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document_id": "550e8400-e29b-41d4-a716-446655440001",
    "parent_id": None,
    "content": "This summary looks correct.",
    "author": {"id": "user-1", "name": "Alice Smith", "avatar": None},
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-01T10:00:00Z",
    "like_count": 3,
    "liked_by_me": False,
    "replies": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "document_id": "550e8400-e29b-41d4-a716-446655440001",
            "parent_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Agreed, section 2 is especially clear.",
            "author": {"id": "user-2", "name": "Bob Jones", "avatar": None},
            "created_at": "2025-01-01T10:05:00Z",
            "updated_at": "2025-01-01T10:05:00Z",
            "like_count": 1,
            "liked_by_me": True,
            "replies": [],
        }
    ],
}

EXAMPLE_PAGINATED_RESPONSE = {
    "items": [EXAMPLE_COMMENT_RESPONSE],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "has_next": True,
}
