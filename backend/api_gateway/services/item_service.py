from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.item import DocumentSummary, Item
from models.processing_job import ProcessingJob
from schemas.document import (
    DocumentDetailResponse,
    DocumentItem,
    FolderItem,
    ProcessingJobResponse,
    UnifiedListResponse,
    decode_cursor,
    encode_cursor,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_folder_item(item: Item) -> FolderItem:
    return FolderItem(
        id=item.id,
        name=item.name,
        description=item.description,
        parent_id=item.parent_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_document_item(item: Item) -> DocumentItem:
    return DocumentItem(
        id=item.id,
        filename=item.name,
        description=item.description,
        mime_type=item.mime_type or "",
        file_size_bytes=item.file_size_bytes or 0,
        status=item.status or "PENDING",
        folder_id=item.parent_id,
        folder_name=item.parent.name if item.parent else None,
        source_url=item.source_url,
        created_at=item.created_at,
        updated_at=item.updated_at,
        processing_jobs=[ProcessingJobResponse.model_validate(j) for j in item.processing_jobs],
    )


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
    item = Item(
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
    await db.refresh(item)
    return item


async def create_link_item(
    db: AsyncSession,
    user_id: UUID,
    url: str,
    title: Optional[str],
    parent_id: Optional[UUID] = None,
) -> Item:
    item = Item(
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
    await db.refresh(item)
    return item


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

    item = Item(type="folder", user_id=user_id, name=name, parent_id=parent_id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


# ── Shared retrieval ──────────────────────────────────────────────────────────

async def get_item(db: AsyncSession, item_id: UUID, user_id: UUID) -> Optional[Item]:
    result = await db.execute(
        select(Item).where(Item.id == item_id, Item.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_document_detail(
    db: AsyncSession, item_id: UUID, user_id: UUID
) -> Optional[DocumentDetailResponse]:
    result = await db.execute(
        select(Item)
        .where(Item.id == item_id, Item.user_id == user_id, Item.type == "document")
        .options(selectinload(Item.processing_jobs), selectinload(Item.parent))
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
) -> list[FolderItem]:
    """Return path from root to folder_id (root first, target last)."""
    path: list[FolderItem] = []
    current_id: Optional[UUID] = folder_id
    visited: set[UUID] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        result = await db.execute(
            select(Item).where(
                Item.id == current_id,
                Item.user_id == user_id,
                Item.type == "folder",
            )
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
            select(Item.id)
            .where(Item.parent_id == parent_id, Item.user_id == user_id)
        )
        cte = base.cte(recursive=True)
        rec = (
            select(Item.id)
            .join(cte, Item.parent_id == cte.c.id)
            .where(Item.user_id == user_id)
        )
        cte = cte.union_all(rec)

        stmt = (
            select(Item)
            .where(Item.id.in_(select(cte.c.id)))
            .options(selectinload(Item.parent), selectinload(Item.processing_jobs))
            .order_by(Item.created_at.desc(), Item.id.desc())
        )
        rows = list((await db.execute(stmt)).scalars().all())
        unified = [
            _to_folder_item(item) if item.type == "folder" else _to_document_item(item)
            for item in rows
        ]
        return UnifiedListResponse(items=unified, next_cursor=None, has_more=False)

    stmt = (
        select(Item)
        .where(Item.user_id == user_id)
        .options(selectinload(Item.parent), selectinload(Item.processing_jobs))
        .order_by(Item.created_at.desc(), Item.id.desc())
    )
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Item.created_at < cursor_ts,
                and_(Item.created_at == cursor_ts, Item.id < cursor_id),
            )
        )
    stmt = stmt.limit(limit + 1)
    rows = list((await db.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
    unified = [
        _to_folder_item(item) if item.type == "folder" else _to_document_item(item)
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
        select(Item).where(Item.id == item_id, Item.user_id == user_id)
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
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: UUID, user_id: UUID) -> Optional[Item]:
    result = await db.execute(
        select(Item).where(Item.id == item_id, Item.user_id == user_id)
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
    stmt = select(Item).where(Item.user_id == user_id, Item.type == "folder")
    if parent_id is None:
        stmt = stmt.where(Item.parent_id.is_(None))
    else:
        stmt = stmt.where(Item.parent_id == parent_id)
    stmt = stmt.order_by(Item.name)
    return list((await db.execute(stmt)).scalars().all())


async def get_processing_jobs(db: AsyncSession, document_id: UUID) -> list[ProcessingJob]:
    result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id)
        .order_by(ProcessingJob.created_at)
    )
    return list(result.scalars().all())
