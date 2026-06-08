import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.user import User
from schemas.document import DocumentDetailResponse, Item, ItemUpdateRequest, LinkCreateRequest, UnifiedListResponse, UploadResponse
from services import document_service as item_service, kafka_producer, storage_service
from schemas.kafka_events import DocumentUploadedEvent, LinkAddedEvent, Topics

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    # Images — text extracted via Tesseract OCR
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/bmp",
    "image/webp",
    "image/gif",
}

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Allowed: PDF, DOCX, XLSX, PPTX, TXT, MD, CSV"
            ),
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    doc = await item_service.create_document_item(
        db=db,
        user_id=current_user.id,
        filename=file.filename or "document",
        minio_key="",
        mime_type=file.content_type,
        file_size_bytes=len(file_bytes),
        parent_id=folder_id,
    )

    minio_key = storage_service.raw_object_key(current_user.id, doc.id, file.filename or "document")
    storage_service.upload_file(
        file_data=file_bytes,
        bucket=settings.minio_bucket_raw,
        object_name=minio_key,
        content_type=file.content_type,
    )

    doc.minio_key = minio_key
    doc.status = "PROCESSING"
    await db.commit()

    event = DocumentUploadedEvent(
        document_id=doc.id,
        user_id=current_user.id,
        minio_key=minio_key,
        filename=doc.name,
        mime_type=file.content_type,
        file_size_bytes=len(file_bytes),
        uploaded_at=datetime.now(timezone.utc),
    )
    await kafka_producer.publish(
        topic=Topics.DOCUMENT_UPLOADED,
        payload=event.to_json(),
        key=str(doc.id),
    )
    logger.info("Document uploaded: document_id=%s user_id=%s", doc.id, current_user.id)

    return UploadResponse(
        document_id=doc.id,
        status="PROCESSING",
        status_ws_url=f"/ws/documents/{doc.id}/ws",
    )


@router.post("/link", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def add_link(
    body: LinkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    url_str = str(body.url)
    doc = await item_service.create_link_item(
        db=db,
        user_id=current_user.id,
        url=url_str,
        title=body.title,
        parent_id=body.folder_id,
    )

    event = LinkAddedEvent(
        document_id=doc.id,
        user_id=current_user.id,
        source_url=url_str,
        filename=doc.name,
        added_at=datetime.now(timezone.utc),
    )
    await kafka_producer.publish(
        topic=Topics.DOCUMENT_UPLOADED,
        payload=event.to_json(),
        key=str(doc.id),
    )
    logger.info("Link added: document_id=%s url=%s user_id=%s", doc.id, url_str, current_user.id)

    return UploadResponse(
        document_id=doc.id,
        status="PROCESSING",
        status_ws_url=f"/ws/documents/{doc.id}/ws",
    )


@router.get("", response_model=UnifiedListResponse)
async def list_items(
    limit: int = 50,
    cursor: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await item_service.list_unified(
        db, current_user.id, limit=limit, cursor=cursor, parent_id=parent_id
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = await item_service.get_document_detail(db, document_id, current_user.id)
    if not detail:
        raise HTTPException(status_code=404, detail="Document not found")
    return detail


@router.patch("/{document_id}", response_model=Item)
async def update_document(
    document_id: UUID,
    body: ItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await item_service.update_item(
        db,
        document_id,
        current_user.id,
        name=body.name,
        description=body.description,
        clear_description=body.description is None and "description" in body.model_fields_set,
        parent_id=body.parent_id,
        clear_parent=body.parent_id is None and "parent_id" in body.model_fields_set,
    )
    if not item or item.type != "document":
        raise HTTPException(status_code=404, detail="Document not found")
    return item_service._to_item(item)


@router.post("/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reset processing state and re-trigger the pipeline from scratch."""
    item = await item_service.reprocess_document(db, document_id, current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")

    event = DocumentUploadedEvent(
        document_id=item.id,
        user_id=current_user.id,
        minio_key=item.minio_key or "",
        filename=item.name,
        mime_type=item.mime_type or "",
        file_size_bytes=item.file_size_bytes or 0,
        uploaded_at=datetime.now(timezone.utc),
    )
    await kafka_producer.publish(
        topic=Topics.DOCUMENT_UPLOADED,
        payload=event.to_json(),
        key=str(item.id),
    )
    logger.info("Reprocess triggered: document_id=%s user_id=%s", item.id, current_user.id)
    return {"status": "reprocessing"}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await item_service.get_item(db, document_id, current_user.id)
    if not item or item.type != "document":
        raise HTTPException(status_code=404, detail="Document not found")

    storage_service.delete_object(settings.minio_bucket_raw, item.minio_key or "")
    storage_service.delete_object(
        settings.minio_bucket_processed,
        storage_service.processed_object_key(document_id),
    )

    await item_service.delete_item(db, document_id, current_user.id)


@router.websocket("/{document_id}/ws")
async def document_status_ws(
    websocket: WebSocket,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()
    try:
        while True:
            jobs = await item_service.get_processing_jobs(db, document_id)
            payload = [
                {"stage": j.stage, "status": j.status, "error": j.error_message}
                for j in jobs
            ]
            await websocket.send_text(json.dumps(payload))

            all_done = all(j.status in ("COMPLETED", "FAILED") for j in jobs)
            if all_done:
                break

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
