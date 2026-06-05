import chromadb
from chromadb.config import Settings

from config import get_settings

settings = get_settings()

_client = None


def get_client():
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_or_create_collection(name: str | None = None) -> chromadb.Collection:
    client = get_client()
    collection_name = name or settings.chroma_collection
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
