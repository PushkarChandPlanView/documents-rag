import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class Item(Base):
    """Single-table entity for folders (type='folder') and documents (type='document').

    Shared columns: id, type, user_id, name, parent_id, created_at, updated_at
    Document-only (NULL on folder rows): mime_type, file_size_bytes, minio_key,
        source_url, status
    Summaries live in document_summaries for versioning.
    """

    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("type IN ('folder', 'document')", name="items_type_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True, index=True
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Document-only columns (NULL for folder rows)
    mime_type: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    minio_key: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    parent: Mapped[Optional["Item"]] = relationship(
        "Item", back_populates="children", remote_side=[id]
    )
    children: Mapped[list["Item"]] = relationship(
        "Item", back_populates="parent", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(  # type: ignore[name-defined]
        "ProcessingJob", back_populates="item", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="item", cascade="all, delete-orphan"
    )
    summaries: Mapped[list["DocumentSummary"]] = relationship(
        "DocumentSummary", back_populates="item", cascade="all, delete-orphan",
        order_by="DocumentSummary.created_at.desc()",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Column stays named document_id so workers' raw SQL needs no change
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item: Mapped["Item"] = relationship("Item", back_populates="chunks")


class DocumentSummary(Base):
    __tablename__ = "document_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item: Mapped["Item"] = relationship("Item", back_populates="summaries")
