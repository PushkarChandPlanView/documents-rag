import io
from typing import BinaryIO
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from config import get_settings

settings = get_settings()

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
    return _client


def ensure_buckets() -> None:
    client = get_minio_client()
    for bucket in [settings.minio_bucket_raw, settings.minio_bucket_processed]:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def upload_file(
    file_data: bytes,
    bucket: str,
    object_name: str,
    content_type: str = "application/octet-stream",
) -> None:
    client = get_minio_client()
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )


def download_file(bucket: str, object_name: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(bucket: str, object_name: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta
    client = get_minio_client()
    return client.presigned_get_object(
        bucket_name=bucket,
        object_name=object_name,
        expires=timedelta(seconds=expires_seconds),
    )


def delete_object(bucket: str, object_name: str) -> None:
    client = get_minio_client()
    try:
        client.remove_object(bucket, object_name)
    except S3Error:
        pass  # already deleted or doesn't exist


def raw_object_key(user_id: UUID, document_id: UUID, filename: str) -> str:
    """Generate MinIO key for raw uploaded file."""
    return f"{user_id}/{document_id}/{filename}"


def processed_object_key(document_id: UUID) -> str:
    """Generate MinIO key for extracted text."""
    return f"{document_id}/text.txt"
