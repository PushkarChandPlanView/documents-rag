from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
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
    kafka_topic_text_extracted: str = "text_extracted"
    kafka_topic_document_chunked: str = "document_chunked"
    kafka_topic_embeddings_generated: str = "embeddings_generated"
    kafka_topic_summary_generated: str = "summary_generated"
    kafka_topic_dlq: str = "dlq.document_errors"

    kafka_consumer_group_text_extraction: str = "text-extraction-workers"
    kafka_consumer_group_chunking: str = "chunking-workers"
    kafka_consumer_group_embedding: str = "embedding-workers"
    kafka_consumer_group_summarization: str = "summarization-workers"

    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "llama3"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_temperature: float = 0.1
    ollama_num_ctx: int = 4096

    # ── Provider selection ────────────────────────────────────────────────────
    # "ollama" (default, local) or "bedrock" (AWS)
    llm_provider: str = "ollama"
    embed_provider: str = "ollama"

    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    aws_region: str = "us-east-1"
    bedrock_llm_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_embed_model: str = "amazon.titan-embed-text-v2:0"
    bedrock_temperature: float = 0.1
    bedrock_max_tokens: int = 512

    # Chunking — units are TOKENS (cl100k_base), not characters
    chunk_size: int = 512
    chunk_overlap: int = 64
    semantic_chunk_threshold_chars: int = 50_000  # still chars — document-size gate


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
