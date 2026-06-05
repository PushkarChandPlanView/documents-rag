import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.user import User
from schemas.document import DocumentListResponse, DocumentResponse, UploadResponse
from services import document_service, kafka_producer, storage_service
from schemas.kafka_events import DocumentUploadedEvent, Topics

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT",
        )

    # Read and validate size
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # Create document record in DB
    doc = await document_service.create_document(
        db=db,
        user_id=current_user.id,
        filename=file.filename or "document",
        minio_key="",  # will be set after MinIO upload
        mime_type=file.content_type,
        file_size_bytes=len(file_bytes),
    )

    # Upload to MinIO
    minio_key = storage_service.raw_object_key(current_user.id, doc.id, file.filename or "document")
    storage_service.upload_file(
        file_data=file_bytes,
        bucket=settings.minio_bucket_raw,
        object_name=minio_key,
        content_type=file.content_type,
    )

    # Update minio_key in DB
    doc.minio_key = minio_key
    doc.status = "PROCESSING"
    await db.commit()

    # Publish Kafka event
    event = DocumentUploadedEvent(
        document_id=doc.id,
        user_id=current_user.id,
        minio_key=minio_key,
        filename=file.filename or "document",
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


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = await document_service.list_documents(db, current_user.id, offset=offset, limit=limit)
    return DocumentListResponse(items=docs, total=len(docs), offset=offset, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await document_service.get_document(db, document_id, current_user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await document_service.get_document(db, document_id, current_user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from MinIO (raw + processed)
    storage_service.delete_object(settings.minio_bucket_raw, doc.minio_key)
    storage_service.delete_object(
        settings.minio_bucket_processed,
        storage_service.processed_object_key(document_id),
    )

    deleted = await document_service.delete_document(db, document_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.websocket("/{document_id}/ws")
async def document_status_ws(
    websocket: WebSocket,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint: pushes processing stage updates to the browser."""
    await websocket.accept()
    try:
        while True:
            jobs = await document_service.get_processing_jobs(db, document_id)
            payload = [
                {"stage": j.stage, "status": j.status, "error": j.error_message}
                for j in jobs
            ]
            await websocket.send_text(json.dumps(payload))

            # Check if pipeline is complete or failed
            all_done = all(j.status in ("COMPLETED", "FAILED") for j in jobs)
            if all_done:
                break

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
