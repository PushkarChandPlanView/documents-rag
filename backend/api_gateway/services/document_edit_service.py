import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sql_text

from config import get_settings
from models.document import DocumentChunk, DocumentSummary
from models.edit import DocumentEdit
from schemas.edit import DocumentEditResponse, EditListResponse
from schemas.kafka_events import DocumentUploadedEvent, TextExtractedEvent, Topics
from services import document_service, kafka_producer, storage_service
from services.format_editors import apply_edit_to_file

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
            json={"document_text": original_content, "instruction": instruction, "mime_type": item.mime_type},
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
        mime_type=item.mime_type,
        raw_minio_key=item.minio_key,
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

    updated_source = False

    # ── Try to edit the actual source file ───────────────────────────────────
    if edit.mime_type and edit.raw_minio_key:
        try:
            raw_bytes = storage_service.download_file(
                settings.minio_bucket_raw, edit.raw_minio_key
            )
            edited_bytes = apply_edit_to_file(
                raw_bytes,
                edit.mime_type,
                edit.original_content,
                edit.proposed_content,
            )
        except Exception as exc:
            logger.warning("Format editor failed (%s), falling back to text-only edit.", exc)
            edited_bytes = None

        if edited_bytes is not None:
            storage_service.upload_file(
                file_data=edited_bytes,
                bucket=settings.minio_bucket_raw,
                object_name=edit.raw_minio_key,
            )
            updated_source = True

    if updated_source:
        # Full pipeline re-run from TEXT_EXTRACTION
        await db.execute(
            sql_text(
                "UPDATE processing_jobs SET status = 'PENDING', started_at = NULL, completed_at = NULL "
                "WHERE document_id = :doc_id"
            ).bindparams(doc_id=edit.document_id)
        )
        await db.execute(
            sql_text("DELETE FROM document_embeddings WHERE document_id = :doc_id").bindparams(
                doc_id=edit.document_id
            )
        )
        await db.execute(sql_delete(DocumentChunk).where(DocumentChunk.document_id == edit.document_id))
        await db.execute(sql_delete(DocumentSummary).where(DocumentSummary.document_id == edit.document_id))
        await db.execute(
            sql_text(
                "UPDATE documents SET status = 'PROCESSING', updated_at = now() WHERE id = :doc_id"
            ).bindparams(doc_id=edit.document_id)
        )
        doc_row = (await db.execute(
            sql_text("SELECT name, file_size_bytes FROM documents WHERE id = :doc_id").bindparams(
                doc_id=edit.document_id
            )
        )).fetchone()

        version_result = await db.execute(
            sql_text(
                "SELECT COUNT(*) FROM document_edits WHERE document_id = :doc_id AND status = 'approved'"
            ).bindparams(doc_id=edit.document_id)
        )
        edit.version = (version_result.scalar() or 0) + 1
        edit.status = "approved"
        await db.commit()

        event = DocumentUploadedEvent(
            document_id=edit.document_id,
            user_id=user_id,
            minio_key=edit.raw_minio_key,
            filename=doc_row.name if doc_row else str(edit.document_id),
            mime_type=edit.mime_type,
            file_size_bytes=doc_row.file_size_bytes if doc_row else 0,
            uploaded_at=datetime.now(timezone.utc),
        )
        await kafka_producer.publish(
            topic=Topics.DOCUMENT_UPLOADED,
            payload=event.to_json(),
            key=str(edit.document_id),
        )
    else:
        # Fallback: write proposed text to processed bucket, restart from CHUNKING
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
            sql_text("DELETE FROM document_embeddings WHERE document_id = :doc_id").bindparams(
                doc_id=edit.document_id
            )
        )
        await db.execute(sql_delete(DocumentChunk).where(DocumentChunk.document_id == edit.document_id))
        await db.execute(sql_delete(DocumentSummary).where(DocumentSummary.document_id == edit.document_id))
        await db.execute(
            sql_text(
                "UPDATE documents SET status = 'PROCESSING', updated_at = now() WHERE id = :doc_id"
            ).bindparams(doc_id=edit.document_id)
        )

        version_result = await db.execute(
            sql_text(
                "SELECT COUNT(*) FROM document_edits WHERE document_id = :doc_id AND status = 'approved'"
            ).bindparams(doc_id=edit.document_id)
        )
        edit.version = (version_result.scalar() or 0) + 1
        edit.status = "approved"
        await db.commit()

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

    await db.refresh(edit)
    logger.info(
        "Edit approved (source_updated=%s): edit_id=%s doc_id=%s",
        updated_source, edit_id, edit.document_id,
    )
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
