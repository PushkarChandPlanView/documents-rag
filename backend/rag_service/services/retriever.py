"""
ChromaDB vector similarity retriever with metadata filtering.
"""
from dataclasses import dataclass
from typing import Optional

import chromadb
from chromadb.config import Settings

from config import get_settings

settings = get_settings()

_client = None


def get_collection():
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    score: float
    chunk_index: int
    page_number: Optional[int]
    user_id: str


def retrieve(
    query_embedding: list[float],
    user_id: str,
    document_ids: Optional[list[str]] = None,
    top_k: int = 20,
) -> list[RetrievedChunk]:
    collection = get_collection()

    if document_ids and len(document_ids) == 1:
        where_filter: dict = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$eq": document_ids[0]}},
            ]
        }
    elif document_ids:
        where_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$in": document_ids}},
            ]
        }
    else:
        where_filter = {"user_id": {"$eq": user_id}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count() or 1),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    if not results["ids"] or not results["ids"][0]:
        return chunks

    for i, chunk_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        score = 1.0 - distance  # cosine distance → similarity

        chunks.append(RetrievedChunk(
            chunk_id=chunk_id,
            document_id=meta.get("document_id", ""),
            text=results["documents"][0][i],
            score=score,
            chunk_index=meta.get("chunk_index", 0),
            page_number=meta.get("page_number") if meta.get("page_number", -1) != -1 else None,
            user_id=meta.get("user_id", ""),
        ))

    return sorted(chunks, key=lambda c: c.score, reverse=True)
