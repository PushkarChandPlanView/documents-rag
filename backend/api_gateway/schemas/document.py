import base64
import json
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class ProcessingJobResponse(BaseModel):
    id: UUID
    stage: str
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Unified item (folders and documents share one shape) ─────────────────────

class Item(BaseModel):
    type: Literal["folder", "document"]
    id: UUID
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    parent_name: Optional[str] = None
    # Document-only (None for folders)
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    processing_jobs: list[ProcessingJobResponse] = []
    compliance_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Backward-compat aliases
FolderItem = Item
DocumentItem = Item
UnifiedItem = Item


class UnifiedListResponse(BaseModel):
    items: list[Item]
    next_cursor: Optional[str] = None
    has_more: bool = False


class ItemUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None


# ── Single-document detail (includes summary + processing jobs) ───────────────

class DocumentDetailResponse(BaseModel):
    type: Literal["document"] = "document"
    id: UUID
    name: str
    filename: str
    description: Optional[str] = None
    mime_type: str
    file_size_bytes: int
    status: str
    folder_id: Optional[UUID] = None
    folder_name: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    summary: Optional[str] = None          # from document_summaries (active)
    created_at: datetime
    updated_at: datetime
    processing_jobs: list[ProcessingJobResponse] = []


# ── Request / response helpers ────────────────────────────────────────────────

class UploadResponse(BaseModel):
    document_id: UUID
    status: str
    status_ws_url: str


class LinkCreateRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    folder_id: Optional[UUID] = None
    source_type: Optional[str] = "url"


# ── Cursor helpers ────────────────────────────────────────────────────────────

def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    payload = {"created_at": created_at.isoformat(), "id": str(item_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])
