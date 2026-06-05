import base64
import json
from datetime import datetime
from typing import Annotated, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ProcessingJobResponse(BaseModel):
    id: UUID
    stage: str
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Unified list items ────────────────────────────────────────────────────────

class FolderItem(BaseModel):
    type: Literal["folder"] = "folder"
    id: UUID
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class DocumentItem(BaseModel):
    type: Literal["document"] = "document"
    id: UUID
    filename: str          # mapped from items.name
    description: Optional[str] = None
    mime_type: str
    file_size_bytes: int
    status: str
    folder_id: Optional[UUID] = None    # mapped from items.parent_id
    folder_name: Optional[str] = None
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processing_jobs: list[ProcessingJobResponse] = []


UnifiedItem = Annotated[
    Union[FolderItem, DocumentItem],
    Field(discriminator="type"),
]


class UnifiedListResponse(BaseModel):
    items: list[Union[FolderItem, DocumentItem]]
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
    filename: str
    mime_type: str
    file_size_bytes: int
    status: str
    folder_id: Optional[UUID] = None
    folder_name: Optional[str] = None
    source_url: Optional[str] = None
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


# ── Cursor helpers ────────────────────────────────────────────────────────────

def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    payload = {"created_at": created_at.isoformat(), "id": str(item_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])
