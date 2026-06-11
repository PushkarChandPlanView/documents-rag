from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_url: str = "postgresql+asyncpg://docstore:changeme@postgres:5432/docstore"

    # ── Provider selection ────────────────────────────────────────────────────
    # "ollama" (default, local) or "bedrock" (AWS)
    llm_provider: str = "bedrock"
    embed_provider: str = "bedrock"

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "llama3"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_temperature: float = 0.1
    ollama_num_ctx: int = 4096
    ollama_num_predict: int = 1024

    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    aws_region: str = "us-east-1"
    bedrock_llm_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_embed_model: str = "amazon.titan-embed-text-v2:0"
    bedrock_temperature: float = 0.1
    bedrock_max_tokens: int = 1024

    # ── Elasticsearch ────────────────────────────────────────────────────────
    elasticsearch_url: str = "http://elasticsearch:9200"
    es_index_chunks: str = "document_chunks"
    es_embedding_dim: int = 1024           # must match the provider's output dim
    es_hybrid_window: int = 50             # RRF window_size (candidates per sub-query)
    es_hybrid_rank_constant: int = 20      # RRF rank_constant

    # ── RAG ───────────────────────────────────────────────────────────────────
    rag_top_k_retrieve: int = 20
    rag_top_k_rerank: int = 8
    rag_min_score: float = 0.0
    rag_context_token_budget: int = 3500


@lru_cache
def get_settings() -> RAGSettings:
    return RAGSettings()
