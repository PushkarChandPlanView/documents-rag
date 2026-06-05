"""
Kafka event payload definitions used by the API gateway.
These mirror the schemas in workers/shared/schemas.py but are
self-contained so api_gateway has no dependency on the workers package.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadedEvent(BaseModel):
    document_id: UUID
    user_id: UUID
    minio_key: str
    filename: str
    mime_type: str
    file_size_bytes: int
    uploaded_at: datetime

    def to_json(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class LinkAddedEvent(BaseModel):
    document_id: UUID
    user_id: UUID
    source_url: str
    filename: str
    added_at: datetime
    # Sentinel values so the text-extraction worker routes it to the URL fetcher
    minio_key: str = ""
    mime_type: str = "text/html"
    file_size_bytes: int = 0

    def to_json(self) -> bytes:
        return self.model_dump_json().encode("utf-8")


class Topics:
    DOCUMENT_UPLOADED = "document_uploaded"
    DLQ = "dlq.document_errors"
