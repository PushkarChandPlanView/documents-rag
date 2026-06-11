"""
Elasticsearch indexer — mirrors the pgvector upsert so every embedded chunk
is also indexed into ES for hybrid search (BM25 + kNN + RRF).

Index mapping is created lazily on the first upsert call so the worker
doesn't fail at startup if ES isn't ready yet (handled by retry logic).
"""
import logging
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_es_client: Optional[AsyncElasticsearch] = None
_index_ready: bool = False


def _get_client() -> AsyncElasticsearch:
    global _es_client
    if _es_client is None:
        _es_client = AsyncElasticsearch(
            settings.elasticsearch_url,
            request_timeout=30,
            retry_on_timeout=True,
            max_retries=3,
        )
    return _es_client


def _index_mapping(dim: int) -> dict:
    """Return the ES index mapping for document chunks."""
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": False,
            "properties": {
                "chunk_id":      {"type": "keyword"},
                "document_id":   {"type": "keyword"},
                "user_id":       {"type": "keyword"},
                "text":          {"type": "text", "analyzer": "english"},
                "document_name": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "file_type":     {"type": "keyword"},
                "chunk_index":        {"type": "integer"},
                "page_number":        {"type": "integer"},
                "char_count":         {"type": "integer"},
                "token_count":        {"type": "integer"},
                "total_chunks":       {"type": "integer"},
                # enriched document-level metadata
                "source_url":         {"type": "keyword"},
                "file_size_bytes":    {"type": "long"},
                "folder_id":          {"type": "keyword"},
                "ingested_at":        {"type": "date"},
                "description": {
                    "type": "text",
                    "analyzer": "english",
                },
                "chunking_strategy":  {"type": "keyword"},
                "source_type":        {"type": "keyword"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": dim,
                    "index": True,
                    "similarity": "cosine",
                },
            },
        },
    }


def _field_mapping_patch() -> dict:
    """Return a minimal PUT-mapping body for non-embedding fields only.

    Used to add new fields to an existing index without recreating it.
    (dense_vector fields cannot be patched; they must exist at creation time.)
    """
    full = _index_mapping(1)["mappings"]["properties"]
    return {
        "properties": {
            k: v for k, v in full.items() if k != "embedding"
        }
    }


async def _ensure_index(dim: int) -> None:
    """Create the index if it doesn't exist, then patch any missing fields."""
    global _index_ready
    if _index_ready:
        return
    es = _get_client()
    exists = await es.indices.exists(index=settings.es_index_chunks)
    if not exists:
        logger.info("Creating ES index '%s' (dim=%d)", settings.es_index_chunks, dim)
        await es.indices.create(index=settings.es_index_chunks, body=_index_mapping(dim))
    else:
        # Patch mapping: adds any new keyword/text fields that don't exist yet.
        # ES ignores fields that are already mapped with the same type.
        try:
            await es.indices.put_mapping(
                index=settings.es_index_chunks,
                body=_field_mapping_patch(),
            )
            logger.info("ES mapping patched for index '%s'", settings.es_index_chunks)
        except Exception as exc:
            logger.warning("ES mapping patch failed (non-fatal): %s", exc)
    _index_ready = True


async def upsert_chunks(rows: list[dict]) -> None:
    """
    Upsert a batch of embedded chunks into Elasticsearch.

    Each row must contain the same fields as pgvector_client.upsert_embeddings:
        chunk_id, document_id, user_id, chunk_index, page_number,
        document_name, file_type, char_count, token_count, total_chunks, embedding
    """
    if not rows:
        return

    dim = len(rows[0]["embedding"])
    await _ensure_index(dim)

    es = _get_client()
    operations = []
    for row in rows:
        operations.append({
            "index": {
                "_index": settings.es_index_chunks,
                "_id": row["chunk_id"],
            }
        })
        operations.append({
            "chunk_id":           row["chunk_id"],
            "document_id":        row["document_id"],
            "user_id":            row["user_id"],
            "text":               row["text"],
            "document_name":      row.get("document_name", ""),
            "file_type":          row.get("file_type", ""),
            "chunk_index":        row.get("chunk_index", 0),
            "page_number":        row.get("page_number"),
            "char_count":         row.get("char_count", 0),
            "token_count":        row.get("token_count", 0),
            "total_chunks":       row.get("total_chunks", 0),
            # enriched metadata
            "source_url":         row.get("source_url"),
            "file_size_bytes":    row.get("file_size_bytes"),
            "folder_id":          row.get("folder_id"),
            "ingested_at":        row.get("ingested_at"),
            "description":        row.get("description"),
            "chunking_strategy":  row.get("chunking_strategy"),
            "source_type":        row.get("source_type"),
            "embedding":          row["embedding"],
        })

    resp = await es.bulk(operations=operations)
    if resp.get("errors"):
        failed = [
            item["index"]["error"]
            for item in resp["items"]
            if item.get("index", {}).get("error")
        ]
        logger.error("ES bulk upsert had %d errors: %s", len(failed), failed[:3])
    else:
        logger.debug("ES bulk upsert succeeded for %d chunks", len(rows))


async def delete_by_document(document_id: str) -> None:
    """Remove all ES chunks belonging to a document."""
    es = _get_client()
    try:
        resp = await es.delete_by_query(
            index=settings.es_index_chunks,
            body={"query": {"term": {"document_id": document_id}}},
        )
        logger.info(
            "ES deleted %d chunks for document_id=%s",
            resp.get("deleted", 0), document_id,
        )
    except NotFoundError:
        pass  # index doesn't exist yet — nothing to delete
