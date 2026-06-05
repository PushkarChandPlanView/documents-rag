from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    postgres_url: str = "postgresql+asyncpg://docstore:changeme@postgres:5432/docstore"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket_raw: str = "documents-raw"
    minio_bucket_processed: str = "documents-processed"
    minio_secure: bool = False

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_document_uploaded: str = "document_uploaded"
    kafka_topic_dlq: str = "dlq.document_errors"

    # Auth
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # RAG Service (internal)
    rag_service_url: str = "http://rag_service:8001"
    rag_top_k_retrieve: int = 20
    rag_top_k_rerank: int = 5

    # API
    max_upload_size_mb: int = 100
    cors_origins: str = "http://localhost:3000,http://localhost"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
