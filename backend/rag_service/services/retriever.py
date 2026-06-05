"""
ChromaDB retriever with hybrid scoring (semantic + keyword) and neighbor expansion.

Scoring:
  final_score = (semantic_weight * cosine_similarity) + (keyword_weight * keyword_overlap)

Keyword overlap = fraction of unique query terms found in the chunk text.
This prevents sections with similar HR vocabulary from outranking chunks
that literally contain the queried topic (e.g. "referral bonus").

Neighbor expansion: for each matched chunk, adjacent chunks (index ± 1)
from the same document are appended to restore context split across boundaries.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

import chromadb
from chromadb.config import Settings

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_client = None

# Hybrid scoring weights (must sum to 1.0)
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT  = 0.3

# Common words that add no signal for keyword matching
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "is", "it",
    "for", "on", "with", "this", "that", "be", "are", "was", "were",
    "can", "will", "do", "does", "have", "has", "from", "by", "at",
    "as", "if", "not", "but", "so", "any", "all", "your", "our",
    "their", "its", "you", "we", "they", "i", "my", "me",
}


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
    document_name: str = ""
    file_type: str = ""


def _query_terms(query: str) -> set[str]:
    words = re.findall(r"[a-z]+", query.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _keyword_score(query_terms: set[str], chunk_text: str) -> float:
    if not query_terms:
        return 0.0
    chunk_lower = chunk_text.lower()
    matched = sum(1 for term in query_terms if term in chunk_lower)
    return matched / len(query_terms)


def _build_where_filter(user_id: str, document_ids: Optional[list[str]]) -> dict:
    if document_ids and len(document_ids) == 1:
        return {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$eq": document_ids[0]}},
            ]
        }
    elif document_ids:
        return {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"document_id": {"$in": document_ids}},
            ]
        }
    return {"user_id": {"$eq": user_id}}


def _fetch_neighbors(
    collection,
    document_id: str,
    user_id: str,
    chunk_indices: list[int],
) -> list[RetrievedChunk]:
    if not chunk_indices:
        return []
    where: dict = {
        "$and": [
            {"user_id": {"$eq": user_id}},
            {"document_id": {"$eq": document_id}},
            {"chunk_index": {"$in": chunk_indices}},
        ]
    }
    try:
        results = collection.get(where=where, include=["documents", "metadatas"])
    except Exception:
        return []

    neighbors = []
    for i, chunk_id in enumerate(results["ids"]):
        meta = results["metadatas"][i]
        neighbors.append(RetrievedChunk(
            chunk_id=chunk_id,
            document_id=meta.get("document_id", ""),
            text=results["documents"][i],
            score=0.0,
            chunk_index=meta.get("chunk_index", 0),
            page_number=meta.get("page_number") if meta.get("page_number", -1) != -1 else None,
            user_id=meta.get("user_id", ""),
            document_name=meta.get("document_name", ""),
            file_type=meta.get("file_type", ""),
        ))
    return neighbors


def _keyword_query(
    collection,
    query_embedding: list[float],
    where_filter: dict,
    where_document: dict,
    top_k: int,
) -> dict:
    """Query with both metadata filter and document keyword filter."""
    try:
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count() or 1),
            where=where_filter,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


def _parse_results(results: dict, terms: set[str]) -> list[RetrievedChunk]:
    chunks = []
    if not results["ids"] or not results["ids"][0]:
        return chunks
    for i, chunk_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        semantic_score = 1.0 - results["distances"][0][i]
        kw_score = _keyword_score(terms, results["documents"][0][i])
        hybrid_score = (SEMANTIC_WEIGHT * semantic_score) + (KEYWORD_WEIGHT * kw_score)
        chunks.append(RetrievedChunk(
            chunk_id=chunk_id,
            document_id=meta.get("document_id", ""),
            text=results["documents"][0][i],
            score=hybrid_score,
            chunk_index=meta.get("chunk_index", 0),
            page_number=meta.get("page_number") if meta.get("page_number", -1) != -1 else None,
            user_id=meta.get("user_id", ""),
            document_name=meta.get("document_name", ""),
            file_type=meta.get("file_type", ""),
        ))
    return chunks


def retrieve(
    query_embedding: list[float],
    user_id: str,
    document_ids: Optional[list[str]] = None,
    top_k: int = 20,
    query: str = "",
) -> list[RetrievedChunk]:
    collection = get_collection()
    where_filter = _build_where_filter(user_id, document_ids)
    terms = _query_terms(query)

    # Stage 1 — keyword-first: filter to chunks that contain the most
    # significant query terms, then rank by semantic similarity within
    # that filtered set. This prevents unrelated sections from winning
    # purely on semantic score.
    chunks: list[RetrievedChunk] = []
    significant = [t for t in terms if len(t) > 4]  # skip short/generic terms

    for term in significant:
        results = _keyword_query(
            collection,
            query_embedding,
            where_filter,
            {"$contains": term},
            top_k,
        )
        matched = _parse_results(results, terms)
        if matched:
            chunks = matched
            logger.info("Keyword-first stage matched %d chunks on term=%r", len(chunks), term)
            break

    # Stage 2 — fallback to pure semantic if keyword stage found nothing
    if not chunks:
        logger.info("Keyword-first found nothing, falling back to semantic search")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count() or 1),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
        chunks = _parse_results(results, terms)

    chunks.sort(key=lambda c: c.score, reverse=True)

    logger.info(
        "Final scores for query=%r top5=%s",
        query,
        [(round(c.score, 3), c.chunk_index) for c in chunks[:5]],
    )

    # Neighbor expansion
    seen_ids = {c.chunk_id for c in chunks}
    by_doc: dict[str, list[RetrievedChunk]] = {}
    for c in chunks:
        by_doc.setdefault(c.document_id, []).append(c)

    neighbors: list[RetrievedChunk] = []
    for doc_id, doc_chunks in by_doc.items():
        neighbor_indices: set[int] = set()
        existing_indices = {c.chunk_index for c in doc_chunks}
        for c in doc_chunks:
            if c.chunk_index > 0:
                neighbor_indices.add(c.chunk_index - 1)
            neighbor_indices.add(c.chunk_index + 1)
        neighbor_indices -= existing_indices

        for n in _fetch_neighbors(collection, doc_id, user_id, list(neighbor_indices)):
            if n.chunk_id not in seen_ids:
                neighbors.append(n)
                seen_ids.add(n.chunk_id)

    logger.info("Expanded with %d neighbor chunks", len(neighbors))

    return chunks + sorted(neighbors, key=lambda c: c.chunk_index)
