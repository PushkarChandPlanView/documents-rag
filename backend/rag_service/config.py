from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_url: str = "postgresql+asyncpg://docstore:changeme@postgres:5432/docstore"

    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_collection: str = "document_chunks"

    ollama_base_url: str = "http://ollama:11434"
    ollama_llm_model: str = "llama3"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_temperature: float = 0.1
    ollama_num_ctx: int = 4096

    rag_top_k_retrieve: int = 20
    rag_top_k_rerank: int = 5
    rag_context_token_budget: int = 3000


@lru_cache
def get_settings() -> RAGSettings:
    return RAGSettings()
