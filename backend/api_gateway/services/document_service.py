import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.document import Document, DocumentChunk
from models.folder import Folder  # noqa: F401
from models.processing_job import ProcessingJob
from schemas.document import DocumentItem, FolderItem, UnifiedListResponse, decode_cursor, encode_cursor


async def create_document(
    db: AsyncSession,
    user_id: UUID,
    filename: str,
    minio_key: str,
    mime_type: str,
    file_size_bytes: int,
    folder_id: Optional[UUID] = None,
) -> Document:
    doc = Document(
        user_id=user_id,
        filename=filename,
        minio_key=minio_key,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        folder_id=folder_id,
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


async def create_link_document(
    db: AsyncSession,
    user_id: UUID,
    url: str,
    title: Optional[str],
    folder_id: Optional[UUID] = None,
) -> Document:
    filename = title or url
    doc = Document(
        user_id=user_id,
        filename=filename[:500],
        minio_key="",
        mime_type="text/html",
        file_size_bytes=0,
        folder_id=folder_id,
        source_url=url,
        status="PENDING",
    )
    db.add(doc)
    await db.flush()

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
        .options(selectinload(Document.processing_jobs), selectinload(Document.folder))
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
        .options(selectinload(Document.processing_jobs), selectinload(Document.folder))
    )
    return list(result.scalars().all())


async def list_unified(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> UnifiedListResponse:
    """Return folders and documents merged into one cursor-paginated list, sorted by created_at DESC."""
    cursor_ts: Optional[datetime] = None
    cursor_id: Optional[UUID] = None
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)

    # Fetch all folders for user (typically small; no separate pagination needed)
    folder_stmt = (
        select(Folder)
        .where(Folder.user_id == user_id)
        .order_by(Folder.created_at.desc(), Folder.id.desc())
    )
    folder_result = await db.execute(folder_stmt)
    folders = list(folder_result.scalars().all())

    # Fetch documents with eager-loaded jobs + folder
    doc_stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .options(selectinload(Document.processing_jobs), selectinload(Document.folder))
    )
    doc_result = await db.execute(doc_stmt)
    documents = list(doc_result.scalars().all())

    # Convert to unified items
    folder_items: list[FolderItem | DocumentItem] = [
        FolderItem(
            id=f.id,
            name=f.name,
            parent_id=f.parent_id,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in folders
    ]
    doc_items: list[FolderItem | DocumentItem] = [
        DocumentItem(
            id=d.id,
            filename=d.filename,
            mime_type=d.mime_type,
            file_size_bytes=d.file_size_bytes,
            status=d.status,
            folder_id=d.folder_id,
            folder_name=d.folder.name if d.folder else None,
            source_url=d.source_url,
            summary=d.summary,
            created_at=d.created_at,
            updated_at=d.updated_at,
            processing_jobs=d.processing_jobs,
        )
        for d in documents
    ]

    # Merge and sort by (created_at DESC, id DESC)
    all_items = sorted(
        folder_items + doc_items,
        key=lambda x: (x.created_at, x.id),
        reverse=True,
    )

    # Apply cursor filter
    if cursor_ts and cursor_id:
        all_items = [
            item for item in all_items
            if (item.created_at, item.id) < (cursor_ts, cursor_id)
        ]

    # Paginate with limit+1 trick to detect has_more
    page = all_items[: limit + 1]
    has_more = len(page) > limit
    page = page[:limit]

    next_cursor: Optional[str] = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(last.created_at, last.id)

    return UnifiedListResponse(items=page, next_cursor=next_cursor, has_more=has_more)


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
