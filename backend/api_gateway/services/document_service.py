import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.document import Document, DocumentChunk
from models.processing_job import ProcessingJob


async def create_document(
    db: AsyncSession,
    user_id: UUID,
    filename: str,
    minio_key: str,
    mime_type: str,
    file_size_bytes: int,
) -> Document:
    doc = Document(
        user_id=user_id,
        filename=filename,
        minio_key=minio_key,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        status="PENDING",
    )
    db.add(doc)
    await db.flush()

    # Pre-create processing jobs for each pipeline stage
    stages = ["TEXT_EXTRACTION", "CHUNKING", "EMBEDDING", "SUMMARIZATION"]
    for stage in stages:
        job = ProcessingJob(document_id=doc.id, stage=stage, status="PENDING")
        db.add(job)

    await db.commit()
    await db.refresh(doc)
    return doc


async def get_document(db: AsyncSession, document_id: UUID, user_id: UUID) -> Optional[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id, Document.user_id == user_id)
        .options(selectinload(Document.processing_jobs))
    )
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession,
    user_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(selectinload(Document.processing_jobs))
    )
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, document_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        return False
    await db.delete(doc)
    await db.commit()
    return True


async def get_processing_jobs(db: AsyncSession, document_id: UUID) -> list[ProcessingJob]:
    result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.created_at)
    )
    return list(result.scalars().all())
