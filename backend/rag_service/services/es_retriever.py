"""
Elasticsearch hybrid retriever — ported from agentic-search project.

Supports three search modes:
  hybrid   — BM25 (keyword) + kNN (vector) fused with Reciprocal Rank Fusion (RRF)
  semantic — pure kNN vector similarity
  keyword  — pure BM25 full-text search

All queries are scoped to a user_id and optionally restricted to specific document_ids.
Query templates live in migrations/templates/ (Jinja2, same pattern as agentic-search).
"""
import json
import logging
import time
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from jinja2 import Environment, FileSystemLoader

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TEMPLATES_DIR = Path(__file__).parent.parent / "migrations" / "templates"

_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

# Lazy ES client — one per process
_es_client: Optional[AsyncElasticsearch] = None


def get_es_client() -> AsyncElasticsearch:
    global _es_client
    if _es_client is None:
        _es_client = AsyncElasticsearch(
            settings.elasticsearch_url,
            request_timeout=30,
            retry_on_timeout=True,
            max_retries=3,
        )
    return _es_client


@dataclass
class ESChunk:
    chunk_id: str
    document_id: str
    user_id: str
    text: str
    score: float
    chunk_index: int
    page_number: Optional[int]
    document_name: str
    file_type: str
    latency_ms: int = 0


# ── Filter builder ─────────────────────────────────────────────────────────────

def _is_valid_uuid(value: str) -> bool:
    try:
        _uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _build_filters(
    user_id: str,
    document_ids: Optional[list[str]] = None,
    source_types: Optional[list[str]] = None,
    file_types: Optional[list[str]] = None,
    folder_id: Optional[str] = None,
) -> list[dict]:
    """Build ES filter clauses.
    user_id is filtered only when it's a valid UUID — emails/unknown values are ignored
    so single-tenant setups can pass any identifier without filtering out all results.
    """
    filters: list[dict] = []
    if user_id and _is_valid_uuid(user_id):
        filters.append({"term": {"user_id": user_id}})
    if document_ids:
        filters.append({"terms": {"document_id": document_ids}})
    if source_types:
        filters.append({"terms": {"source_type": source_types}})
    if file_types:
        filters.append({"terms": {"file_type": file_types}})
    if folder_id:
        filters.append({"term": {"folder_id": folder_id}})
    return filters


# ── Template renderer ──────────────────────────────────────────────────────────

def _render(template_name: str, **kwargs) -> dict:
    tmpl = _jinja_env.get_template(f"{template_name}.jinja2")
    rendered = tmpl.render(**kwargs)
    return json.loads(rendered)


# ── Public search functions ────────────────────────────────────────────────────

async def hybrid_search(
    query_text: str,
    query_vector: list[float],
    user_id: str,
    document_ids: Optional[list[str]] = None,
    top_k: int = 10,
    source_types: Optional[list[str]] = None,
    file_types: Optional[list[str]] = None,
    folder_id: Optional[str] = None,
) -> list[ESChunk]:
    """
    BM25 + kNN hybrid search fused with script_score cosine similarity.

    Uses the same Jinja2 template pattern as agentic-search/template_query.py
    but adapted for the documents-rag chunk schema and external embeddings.
    """
    filters = _build_filters(user_id, document_ids, source_types, file_types, folder_id)
    body = _render(
        "hybrid_search",
        query_text=query_text,
        query_vector=query_vector,
        filters=filters,
        size=top_k,
        num_candidates=top_k * 10,
        window_size=settings.es_hybrid_window,
        rank_constant=settings.es_hybrid_rank_constant,
    )
    return await _execute(body, top_k)


async def semantic_search(
    query_vector: list[float],
    user_id: str,
    document_ids: Optional[list[str]] = None,
    top_k: int = 10,
    source_types: Optional[list[str]] = None,
    file_types: Optional[list[str]] = None,
    folder_id: Optional[str] = None,
) -> list[ESChunk]:
    """Pure kNN vector similarity search."""
    filters = _build_filters(user_id, document_ids, source_types, file_types, folder_id)
    body = _render(
        "semantic_search",
        query_vector=query_vector,
        filters=filters,
        size=top_k,
        num_candidates=top_k * 10,
    )
    return await _execute(body, top_k)


async def keyword_search(
    query_text: str,
    user_id: str,
    document_ids: Optional[list[str]] = None,
    top_k: int = 10,
    source_types: Optional[list[str]] = None,
    file_types: Optional[list[str]] = None,
    folder_id: Optional[str] = None,
) -> list[ESChunk]:
    """Pure BM25 full-text search (no vectors needed)."""
    filters = _build_filters(user_id, document_ids, source_types, file_types, folder_id)
    body = _render(
        "keyword_search",
        query_text=query_text,
        filters=filters,
        size=top_k,
    )
    return await _execute(body, top_k)


# ── Internal executor ──────────────────────────────────────────────────────────

async def _execute(body: dict, top_k: int) -> list[ESChunk]:
    es = get_es_client()
    t0 = time.perf_counter()
    try:
        resp = await es.search(index=settings.es_index_chunks, body=body)
    except NotFoundError:
        logger.warning("ES index '%s' not found — no results returned", settings.es_index_chunks)
        return []
    latency_ms = int((time.perf_counter() - t0) * 1000)

    chunks = []
    for hit in resp["hits"]["hits"]:
        src = hit["_source"]
        chunks.append(ESChunk(
            chunk_id=src.get("chunk_id", hit["_id"]),
            document_id=src.get("document_id", ""),
            user_id=src.get("user_id", ""),
            text=src.get("text", ""),
            score=hit.get("_score") or 0.0,
            chunk_index=src.get("chunk_index", 0),
            page_number=src.get("page_number"),
            document_name=src.get("document_name", ""),
            file_type=src.get("file_type", ""),
            latency_ms=latency_ms,
        ))

    logger.info(
        "ES search returned %d hits in %dms (index=%s)",
        len(chunks), latency_ms, settings.es_index_chunks,
    )
    return chunks


# ── Health check ───────────────────────────────────────────────────────────────

async def ping() -> bool:
    """Return True if Elasticsearch is reachable."""
    try:
        return await get_es_client().ping()
    except Exception:
        return False
