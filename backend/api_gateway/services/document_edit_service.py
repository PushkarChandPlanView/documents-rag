import logging
from uuid import UUID

import httpx
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sql_text

from config import get_settings
from models.document import DocumentChunk, DocumentSummary
from models.edit import DocumentEdit
from schemas.edit import DocumentEditResponse, EditListResponse
from schemas.kafka_events import TextExtractedEvent, Topics
from services import document_service, kafka_producer, storage_service

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_EDIT_CONTENT_CHARS = 80_000


async def create_edit_draft(
    doc_id: UUID,
    user_id: UUID,
    instruction: str,
    db: AsyncSession,
) -> DocumentEditResponse:
    item = await document_service.get_item(db, doc_id, user_id)
    if not item or item.type != "document":
        raise ValueError("Document not found")

    text_key = f"{doc_id}/text.txt"
    try:
        original_bytes = storage_service.download_file(settings.minio_bucket_processed, text_key)
        original_content = original_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        raise ValueError(f"Could not read document content: {exc}") from exc

    if len(original_content) > MAX_EDIT_CONTENT_CHARS:
        original_content = original_content[:MAX_EDIT_CONTENT_CHARS]

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{settings.rag_service_url}/edit",
            json={"document_text": original_content, "instruction": instruction},
        )
        resp.raise_for_status()
    proposed_content = resp.json()["proposed_text"]

    edit = DocumentEdit(
        document_id=doc_id,
        user_id=user_id,
        instruction=instruction,
        original_content=original_content,
        proposed_content=proposed_content,
        status="pending",
    )
    db.add(edit)
    await db.commit()
    await db.refresh(edit)
    return DocumentEditResponse.model_validate(edit)


async def approve_edit(
    edit_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> DocumentEditResponse:
    result = await db.execute(
        select(DocumentEdit).where(
            DocumentEdit.id == edit_id,
            DocumentEdit.user_id == user_id,
        )
    )
    edit = result.scalar_one_or_none()
    if not edit:
        raise ValueError("Edit not found")
    if edit.status != "pending":
        raise ValueError(f"Edit is already {edit.status}")

    text_key = f"{edit.document_id}/text.txt"
    storage_service.upload_file(
        file_data=edit.proposed_content.encode("utf-8"),
        bucket=settings.minio_bucket_processed,
        object_name=text_key,
        content_type="text/plain",
    )

    await db.execute(
        sql_text(
            "UPDATE processing_jobs SET status = 'PENDING', started_at = NULL, completed_at = NULL "
            "WHERE document_id = :doc_id AND stage IN ('CHUNKING', 'EMBEDDING', 'SUMMARIZATION')"
        ).bindparams(doc_id=edit.document_id)
    )
    await db.execute(
        sql_text(
            "UPDATE documents SET status = 'PROCESSING', updated_at = now() WHERE id = :doc_id"
        ).bindparams(doc_id=edit.document_id)
    )

    # Clear stale derived data — will be rebuilt by the pipeline
    await db.execute(
        sql_text("DELETE FROM document_embeddings WHERE document_id = :doc_id").bindparams(
            doc_id=edit.document_id
        )
    )
    await db.execute(sql_delete(DocumentChunk).where(DocumentChunk.document_id == edit.document_id))
    await db.execute(
        sql_delete(DocumentSummary).where(DocumentSummary.document_id == edit.document_id)
    )

    version_result = await db.execute(
        sql_text(
            "SELECT COUNT(*) FROM document_edits WHERE document_id = :doc_id AND status = 'approved'"
        ).bindparams(doc_id=edit.document_id)
    )
    edit.version = (version_result.scalar() or 0) + 1
    edit.status = "approved"
    await db.commit()
    await db.refresh(edit)

    event = TextExtractedEvent(
        document_id=edit.document_id,
        user_id=user_id,
        text_minio_key=text_key,
        char_count=len(edit.proposed_content),
        page_count=0,
        language="en",
    )
    await kafka_producer.publish(
        topic=Topics.TEXT_EXTRACTED,
        payload=event.to_json(),
        key=str(edit.document_id),
    )
    logger.info("Edit approved and pipeline re-triggered: edit_id=%s doc_id=%s", edit_id, edit.document_id)
    return DocumentEditResponse.model_validate(edit)


async def reject_edit(
    edit_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> DocumentEditResponse:
    result = await db.execute(
        select(DocumentEdit).where(
            DocumentEdit.id == edit_id,
            DocumentEdit.user_id == user_id,
        )
    )
    edit = result.scalar_one_or_none()
    if not edit:
        raise ValueError("Edit not found")
    edit.status = "rejected"
    await db.commit()
    await db.refresh(edit)
    return DocumentEditResponse.model_validate(edit)


async def list_edits(
    doc_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> EditListResponse:
    result = await db.execute(
        select(DocumentEdit)
        .where(DocumentEdit.document_id == doc_id, DocumentEdit.user_id == user_id)
        .order_by(DocumentEdit.created_at.desc())
    )
    edits = [DocumentEditResponse.model_validate(e) for e in result.scalars().all()]
    return EditListResponse(edits=edits)
