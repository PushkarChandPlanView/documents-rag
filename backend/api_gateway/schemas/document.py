from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProcessingJobResponse(BaseModel):
    id: UUID
    stage: str
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    mime_type: str
    file_size_bytes: int
    status: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processing_jobs: list[ProcessingJobResponse] = []

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    offset: int
    limit: int


class UploadResponse(BaseModel):
    document_id: UUID
    status: str
    status_ws_url: str
