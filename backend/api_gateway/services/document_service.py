from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.document import DocumentChunk, DocumentSummary, Item as ItemModel
from models.processing_job import ProcessingJob
from schemas.document import (
    DocumentDetailResponse,
    Item,
    ProcessingJobResponse,
    UnifiedListResponse,
    decode_cursor,
    encode_cursor,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_item(item: ItemModel) -> Item:
    return Item(
        type=item.type,
        id=item.id,
        name=item.name,
        description=item.description,
        parent_id=item.parent_id,
        parent_name=item.parent.name if item.parent else None,
        mime_type=item.mime_type,
        file_size_bytes=item.file_size_bytes,
        status=item.status,
        source_url=item.source_url,
        processing_jobs=[ProcessingJobResponse.model_validate(j) for j in item.processing_jobs],
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# backward compat
_to_folder_item = _to_item
_to_document_item = _to_item


async def _load_item(db: AsyncSession, item_id: UUID) -> Optional[ItemModel]:
    """Fetch a single item with parent + processing_jobs eagerly loaded."""
    result = await db.execute(
        select(ItemModel)
        .where(ItemModel.id == item_id)
        .options(selectinload(ItemModel.parent), selectinload(ItemModel.processing_jobs))
    )
    return result.scalar_one_or_none()


# ── Document items ────────────────────────────────────────────────────────────

async def create_document_item(
    db: AsyncSession,
    user_id: UUID,
    filename: str,
    minio_key: str,
    mime_type: str,
    file_size_bytes: int,
    parent_id: Optional[UUID] = None,
) -> Item:
    item = ItemModel(
        type="document",
        user_id=user_id,
        name=filename,
        minio_key=minio_key,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        parent_id=parent_id,
        status="PENDING",
    )
    db.add(item)
    await db.flush()

    for stage in ["TEXT_EXTRACTION", "CHUNKING", "EMBEDDING", "SUMMARIZATION"]:
        db.add(ProcessingJob(document_id=item.id, stage=stage, status="PENDING"))

    await db.commit()
    return await _load_item(db, item.id)


async def create_link_item(
    db: AsyncSession,
    user_id: UUID,
    url: str,
    title: Optional[str],
    parent_id: Optional[UUID] = None,
) -> Item:
    item = ItemModel(
        type="document",
        user_id=user_id,
        name=(title or url)[:500],
        minio_key="",
        mime_type="text/html",
        file_size_bytes=0,
        parent_id=parent_id,
        source_url=url,
        status="PENDING",
    )
    db.add(item)
    await db.flush()

    for stage in ["TEXT_EXTRACTION", "CHUNKING", "EMBEDDING", "SUMMARIZATION"]:
        db.add(ProcessingJob(document_id=item.id, stage=stage, status="PENDING"))

    await db.commit()
    return await _load_item(db, item.id)


# ── Folder items ──────────────────────────────────────────────────────────────

async def create_folder_item(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    parent_id: Optional[UUID] = None,
) -> Item:
    if parent_id:
        parent = await get_item(db, parent_id, user_id)
        if not parent or parent.type != "folder":
            raise ValueError("Parent folder not found")

    item = ItemModel(type="folder", user_id=user_id, name=name, parent_id=parent_id)
    db.add(item)
    await db.commit()
    return await _load_item(db, item.id)


# ── Shared retrieval ──────────────────────────────────────────────────────────

async def get_item(db: AsyncSession, item_id: UUID, user_id: UUID) -> Optional[Item]:
    result = await db.execute(
        select(ItemModel).where(ItemModel.id == item_id, ItemModel.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_documents_by_ids(
    db: AsyncSession,
    document_ids: list[UUID],
    user_id: UUID,
) -> dict[UUID, ItemModel]:
    if not document_ids:
        return {}
    result = await db.execute(
        select(ItemModel).where(
            ItemModel.id.in_(document_ids),
            ItemModel.user_id == user_id,
            ItemModel.type == "document",
        )
    )
    return {row.id: row for row in result.scalars().all()}


async def get_document_detail(
    db: AsyncSession, item_id: UUID, user_id: UUID
) -> Optional[DocumentDetailResponse]:
    result = await db.execute(
        select(ItemModel)
        .where(ItemModel.id == item_id, ItemModel.user_id == user_id, ItemModel.type == "document")
        .options(selectinload(ItemModel.processing_jobs), selectinload(ItemModel.parent))
    )
    item = result.scalar_one_or_none()
    if not item:
        return None

    summary_result = await db.execute(
        select(DocumentSummary)
        .where(DocumentSummary.document_id == item_id, DocumentSummary.is_active.is_(True))
        .order_by(DocumentSummary.created_at.desc())
        .limit(1)
    )
    summary_row = summary_result.scalar_one_or_none()

    return DocumentDetailResponse(
        id=item.id,
        filename=item.name,
        mime_type=item.mime_type or "",
        file_size_bytes=item.file_size_bytes or 0,
        status=item.status or "PENDING",
        folder_id=item.parent_id,
        folder_name=item.parent.name if item.parent else None,
        source_url=item.source_url,
        summary=summary_row.summary if summary_row else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
        processing_jobs=[
            ProcessingJobResponse.model_validate(j) for j in item.processing_jobs
        ],
    )


async def get_breadcrumb(
    db: AsyncSession, folder_id: UUID, user_id: UUID
) -> list[Item]:
    """Return path from root to folder_id (root first, target last)."""
    path: list[Item] = []
    current_id: Optional[UUID] = folder_id
    visited: set[UUID] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        result = await db.execute(
            select(ItemModel)
            .where(
                ItemModel.id == current_id,
                ItemModel.user_id == user_id,
                ItemModel.type == "folder",
            )
            .options(selectinload(ItemModel.parent), selectinload(ItemModel.processing_jobs))
        )
        item = result.scalar_one_or_none()
        if not item:
            break
        path.append(_to_folder_item(item))
        current_id = item.parent_id
    return list(reversed(path))


async def list_unified(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 50,
    cursor: Optional[str] = None,
    parent_id: Optional[UUID] = None,
) -> UnifiedListResponse:
    if parent_id is not None:
        base = (
            select(ItemModel.id)
            .where(ItemModel.parent_id == parent_id, ItemModel.user_id == user_id)
        )
        cte = base.cte(recursive=True)
        rec = (
            select(ItemModel.id)
            .join(cte, ItemModel.parent_id == cte.c.id)
            .where(ItemModel.user_id == user_id)
        )
        cte = cte.union_all(rec)

        stmt = (
            select(ItemModel)
            .where(ItemModel.id.in_(select(cte.c.id)))
            .options(selectinload(ItemModel.parent), selectinload(ItemModel.processing_jobs))
            .order_by(ItemModel.created_at.desc(), ItemModel.id.desc())
        )
        rows = list((await db.execute(stmt)).scalars().all())
        unified = [
            _to_item(item)
            for item in rows
        ]
        return UnifiedListResponse(items=unified, next_cursor=None, has_more=False)

    stmt = (
        select(ItemModel)
        .where(ItemModel.user_id == user_id)
        .options(selectinload(ItemModel.parent), selectinload(ItemModel.processing_jobs))
        .order_by(ItemModel.created_at.desc(), ItemModel.id.desc())
    )
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                ItemModel.created_at < cursor_ts,
                and_(Item.created_at == cursor_ts, ItemModel.id < cursor_id),
            )
        )
    stmt = stmt.limit(limit + 1)
    rows = list((await db.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
    unified = [
        _to_item(item)
        for item in page
    ]
    return UnifiedListResponse(items=unified, next_cursor=next_cursor, has_more=has_more)


async def update_item(
    db: AsyncSession,
    item_id: UUID,
    user_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    clear_description: bool = False,
    parent_id: Optional[UUID] = None,
    clear_parent: bool = False,
) -> Optional[Item]:
    result = await db.execute(
        select(ItemModel).where(ItemModel.id == item_id, ItemModel.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        return None
    if name is not None:
        item.name = name
    if clear_description:
        item.description = None
    elif description is not None:
        item.description = description
    if clear_parent:
        item.parent_id = None
    elif parent_id is not None:
        item.parent_id = parent_id
    item.updated_at = datetime.utcnow()
    await db.commit()
    return await _load_item(db, item.id)


async def reprocess_document(
    db: AsyncSession,
    document_id: UUID,
    user_id: UUID,
) -> Optional[ItemModel]:
    """Reset processing state and return the item so the router can re-publish the Kafka event."""
    result = await db.execute(
        select(ItemModel)
        .where(ItemModel.id == document_id, ItemModel.user_id == user_id, ItemModel.type == "document")
        .options(selectinload(ItemModel.processing_jobs))
    )
    item = result.scalar_one_or_none()
    if not item:
        return None

    # Clear partial results — delete embeddings first (FK cascade would handle
    # it via document_chunks, but we delete explicitly for clarity and safety)
    from sqlalchemy import delete as sql_delete, text as sql_text
    await db.execute(sql_text(
        "DELETE FROM document_embeddings WHERE document_id = :doc_id"
    ).bindparams(doc_id=document_id))
    await db.execute(sql_delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    await db.execute(sql_delete(DocumentSummary).where(DocumentSummary.document_id == document_id))

    # Reset all processing jobs
    for job in item.processing_jobs:
        job.status = "PENDING"
        job.error_message = None
        job.started_at = None
        job.completed_at = None

    item.status = "PROCESSING"
    item.updated_at = datetime.utcnow()
    await db.commit()
    return item


async def delete_item(db: AsyncSession, item_id: UUID, user_id: UUID) -> Optional[Item]:
    result = await db.execute(
        select(ItemModel).where(ItemModel.id == item_id, ItemModel.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        return None
    await db.delete(item)
    await db.commit()
    return item


async def list_folders(
    db: AsyncSession,
    user_id: UUID,
    parent_id: Optional[UUID] = None,
) -> list[Item]:
    stmt = select(ItemModel).where(ItemModel.user_id == user_id, ItemModel.type == "folder")
    if parent_id is None:
        stmt = stmt.where(ItemModel.parent_id.is_(None))
    else:
        stmt = stmt.where(ItemModel.parent_id == parent_id)
    stmt = stmt.order_by(ItemModel.name)
    return list((await db.execute(stmt)).scalars().all())


async def get_processing_jobs(db: AsyncSession, document_id: UUID) -> list[ProcessingJob]:
    result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.created_at)
    )
    return list(result.scalars().all())
