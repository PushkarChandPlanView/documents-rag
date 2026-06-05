"""
Kafka message payload schemas — the contract between all pipeline services.
All producers and consumers must use these models for serialization.
"""
from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_serializer


class KafkaMessage(BaseModel):
    """Base class for all Kafka message payloads."""

    model_config = {"use_enum_values": True}

    def to_json(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_json(cls, data: bytes) -> "KafkaMessage":
        return cls.model_validate_json(data)


# ─────────────────────────────────────────────────────────────────────────────
# Topic: document_uploaded
# Producer: api_gateway   Consumer: worker_text_extraction
# ─────────────────────────────────────────────────────────────────────────────
class DocumentUploadedEvent(KafkaMessage):
    document_id: UUID
    user_id: UUID
    minio_key: str          # key in documents-raw bucket
    filename: str
    mime_type: str          # application/pdf | application/vnd.openxmlformats-officedocument... | text/plain
    file_size_bytes: int
    uploaded_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Topic: text_extracted
# Producer: worker_text_extraction   Consumer: worker_chunking
# ─────────────────────────────────────────────────────────────────────────────
class TextExtractedEvent(KafkaMessage):
    document_id: UUID
    user_id: UUID
    text_minio_key: str     # key in documents-processed bucket
    char_count: int
    page_count: int
    language: str           # ISO 639-1 code, e.g. "en"


# ─────────────────────────────────────────────────────────────────────────────
# Topic: document_chunked
# Producer: worker_chunking   Consumer: worker_embedding
# ─────────────────────────────────────────────────────────────────────────────
class DocumentChunkedEvent(KafkaMessage):
    document_id: UUID
    user_id: UUID
    chunk_count: int
    chunking_strategy: str  # "recursive_character" | "semantic"


# ─────────────────────────────────────────────────────────────────────────────
# Topic: embeddings_generated
# Producer: worker_embedding   Consumer: worker_summarization
# ─────────────────────────────────────────────────────────────────────────────
class EmbeddingsGeneratedEvent(KafkaMessage):
    document_id: UUID
    user_id: UUID
    vector_count: int
    embedding_model: str    # e.g. "nomic-embed-text"
    embedding_dim: int      # vector dimension, e.g. 768


# ─────────────────────────────────────────────────────────────────────────────
# Topic: summary_generated
# Producer: worker_summarization   Consumer: api_gateway (status)
# ─────────────────────────────────────────────────────────────────────────────
class SummaryGeneratedEvent(KafkaMessage):
    document_id: UUID
    user_id: UUID
    summary_length: int     # character count of summary
    strategy: str           # "single_pass" | "map_reduce"


# ─────────────────────────────────────────────────────────────────────────────
# Topic: dlq.document_errors (Dead Letter Queue)
# Producer: any worker on unrecoverable error
# ─────────────────────────────────────────────────────────────────────────────
class DocumentErrorEvent(KafkaMessage):
    document_id: Optional[UUID] = None
    source_topic: str
    error_type: str
    error_message: str
    original_payload: str   # raw JSON of the failed message
    failed_at: datetime
    retry_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Topic name constants — import these instead of hardcoding strings
# ─────────────────────────────────────────────────────────────────────────────
class Topics:
    DOCUMENT_UPLOADED = "document_uploaded"
    TEXT_EXTRACTED = "text_extracted"
    DOCUMENT_CHUNKED = "document_chunked"
    EMBEDDINGS_GENERATED = "embeddings_generated"
    SUMMARY_GENERATED = "summary_generated"
    DLQ = "dlq.document_errors"


# ─────────────────────────────────────────────────────────────────────────────
# Processing stage enums (mirror DB enums)
# ─────────────────────────────────────────────────────────────────────────────
class ProcessingStage(str, Enum):
    TEXT_EXTRACTION = "TEXT_EXTRACTION"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    SUMMARIZATION = "SUMMARIZATION"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
