"""
Text Extraction Worker
Consumes: document_uploaded
Publishes: text_extracted
"""
import logging
from datetime import datetime, timezone

from aiokafka import ConsumerRecord
from langdetect import detect, LangDetectException
from sqlalchemy import update

from base.base_consumer import BaseConsumer
from base.base_producer import publish
from config import get_settings
from shared import db_client, minio_client
from shared.schemas import DocumentUploadedEvent, TextExtractedEvent, Topics
from .extractors import docx_extractor, pdf_extractor, pptx_extractor, txt_extractor, url_extractor, xlsx_extractor

logger = logging.getLogger(__name__)
settings = get_settings()

MIME_EXTRACTOR_MAP = {
    "application/pdf": pdf_extractor.extract,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": docx_extractor.extract,
    "application/msword": docx_extractor.extract,
    "text/plain": txt_extractor.extract,
    "text/markdown": txt_extractor.extract,
    "text/csv": txt_extractor.extract,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": xlsx_extractor.extract,
    "application/vnd.ms-excel": xlsx_extractor.extract,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": pptx_extractor.extract,
    "application/vnd.ms-powerpoint": pptx_extractor.extract,
}


class TextExtractionConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=settings.kafka_topic_document_uploaded,
            group_id=settings.kafka_consumer_group_text_extraction,
        )

    async def process_message(self, message: ConsumerRecord) -> None:
        event = DocumentUploadedEvent.from_json(message.value)
        doc_id = str(event.document_id)
        logger.info("Processing text extraction for document_id=%s mime=%s", doc_id, event.mime_type)

        async with await db_client.get_session() as session:
            # Mark TEXT_EXTRACTION as IN_PROGRESS
            await session.execute(
                update_processing_job(event.document_id, "TEXT_EXTRACTION", "IN_PROGRESS")
            )
            await session.commit()

        # Link documents: fetch URL content instead of downloading from MinIO
        if event.mime_type == "text/html" and not event.minio_key:
            source_url = await _get_source_url(event.document_id)
            if not source_url:
                raise ValueError(f"No source_url for link document {doc_id}")
            result = url_extractor.extract_from_url(source_url)
        else:
            # Download raw file from MinIO
            file_bytes = minio_client.download(settings.minio_bucket_raw, event.minio_key)

            extractor = MIME_EXTRACTOR_MAP.get(event.mime_type)
            if not extractor:
                raise ValueError(f"No extractor for mime_type: {event.mime_type}")
            result = extractor(file_bytes)

        # Detect language
        try:
            language = detect(result.text[:2000])
        except LangDetectException:
            language = "en"

        # Upload extracted text to MinIO
        text_key = f"{event.document_id}/text.txt"
        minio_client.upload(
            bucket=settings.minio_bucket_processed,
            key=text_key,
            data=result.text.encode("utf-8"),
            content_type="text/plain",
        )

        async with await db_client.get_session() as session:
            # Mark TEXT_EXTRACTION as COMPLETED
            await session.execute(
                update_processing_job(event.document_id, "TEXT_EXTRACTION", "COMPLETED", completed=True)
            )
            await session.commit()

        # Publish next event
        next_event = TextExtractedEvent(
            document_id=event.document_id,
            user_id=event.user_id,
            text_minio_key=text_key,
            char_count=len(result.text),
            page_count=result.page_count,
            language=language,
        )
        await publish(
            topic=Topics.TEXT_EXTRACTED,
            event=next_event,
            key=doc_id,
        )
        logger.info("Text extraction complete for document_id=%s chars=%d", doc_id, len(result.text))


async def _get_source_url(document_id) -> str | None:
    from sqlalchemy import select, text as sql_text
    async with await db_client.get_session() as session:
        result = await session.execute(
            sql_text("SELECT source_url FROM documents WHERE id = :doc_id").bindparams(doc_id=document_id)
        )
        row = result.fetchone()
        return row[0] if row else None


def update_processing_job(document_id, stage: str, status: str, completed: bool = False):
    from sqlalchemy import text as sql_text
    now = datetime.now(timezone.utc)

    # Use inline string literals for enum columns (stage, status) so PostgreSQL
    # can cast them implicitly — asyncpg sends bind params as VARCHAR which
    # PostgreSQL won't auto-cast to a custom enum type.
    if completed:
        return sql_text(
            f"UPDATE processing_jobs SET status = '{status}', completed_at = :completed_at "
            f"WHERE document_id = :doc_id AND stage = '{stage}'"
        ).bindparams(completed_at=now, doc_id=document_id)
    else:
        return sql_text(
            f"UPDATE processing_jobs SET status = '{status}', started_at = :started_at "
            f"WHERE document_id = :doc_id AND stage = '{stage}'"
        ).bindparams(started_at=now, doc_id=document_id)
