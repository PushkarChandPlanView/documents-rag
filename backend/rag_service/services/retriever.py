"""
pgvector retriever with hybrid scoring (semantic + keyword) and neighbor expansion.

Replaces the ChromaDB retriever. All vector data now lives in the
`document_embeddings` table in PostgreSQL; chunk text is JOINed from
`document_chunks`.

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

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

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

_engine = None
_session_factory = None


def _get_session_factory() -> async_sessionmaker:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_async_engine(
            settings.postgres_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


def _new_session() -> AsyncSession:
    return _get_session_factory()()


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


def _embedding_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def _semantic_search(
    session: AsyncSession,
    embedding: list[float],
    user_id: str,
    document_ids: Optional[list[str]],
    top_k: int,
) -> list[dict]:
    """Run a cosine similarity search using pgvector's <=> operator."""
    emb_literal = _embedding_literal(embedding)

    if document_ids and len(document_ids) == 1:
        where_clause = "de.user_id = CAST(:user_id AS uuid) AND de.document_id = CAST(:doc_id AS uuid)"
        params: dict = {"user_id": user_id, "doc_id": document_ids[0],
                        "embedding": emb_literal, "top_k": top_k}
    elif document_ids:
        where_clause = "de.user_id = CAST(:user_id AS uuid) AND de.document_id = ANY(CAST(:doc_ids AS uuid[]))"
        params = {"user_id": user_id, "doc_ids": document_ids,
                  "embedding": emb_literal, "top_k": top_k}
    else:
        where_clause = "de.user_id = CAST(:user_id AS uuid)"
        params = {"user_id": user_id, "embedding": emb_literal, "top_k": top_k}

    result = await session.execute(
        sql_text(f"""
            SELECT
                de.chunk_id::text,
                de.document_id::text,
                de.user_id::text,
                de.chunk_index,
                de.page_number,
                de.document_name,
                de.file_type,
                dc.text,
                (de.embedding <=> CAST(:embedding AS vector)) AS distance
            FROM document_embeddings de
            JOIN document_chunks dc ON dc.id = de.chunk_id
            WHERE {where_clause}
            ORDER BY distance ASC
            LIMIT :top_k
        """),
        params,
    )
    return [dict(r._mapping) for r in result.fetchall()]


async def _fetch_neighbors(
    session: AsyncSession,
    document_id: str,
    user_id: str,
    chunk_indices: list[int],
) -> list[RetrievedChunk]:
    if not chunk_indices:
        return []
    result = await session.execute(
        sql_text("""
            SELECT
                de.chunk_id::text,
                de.document_id::text,
                de.user_id::text,
                de.chunk_index,
                de.page_number,
                de.document_name,
                de.file_type,
                dc.text
            FROM document_embeddings de
            JOIN document_chunks dc ON dc.id = de.chunk_id
            WHERE de.user_id = CAST(:user_id AS uuid)
              AND de.document_id = CAST(:doc_id AS uuid)
              AND de.chunk_index = ANY(:indices)
        """),
        {"user_id": user_id, "doc_id": document_id, "indices": chunk_indices},
    )
    neighbors = []
    for row in result.fetchall():
        r = dict(row._mapping)
        neighbors.append(RetrievedChunk(
            chunk_id=r["chunk_id"],
            document_id=r["document_id"],
            text=r["text"],
            score=0.0,
            chunk_index=r["chunk_index"],
            page_number=r["page_number"],
            user_id=r["user_id"],
            document_name=r.get("document_name", ""),
            file_type=r.get("file_type", ""),
        ))
    return neighbors


def _rows_to_chunks(rows: list[dict], terms: set[str]) -> list[RetrievedChunk]:
    chunks = []
    for row in rows:
        semantic_score = 1.0 - row["distance"]
        kw_score = _keyword_score(terms, row["text"])
        hybrid_score = (SEMANTIC_WEIGHT * semantic_score) + (KEYWORD_WEIGHT * kw_score)
        chunks.append(RetrievedChunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            text=row["text"],
            score=hybrid_score,
            chunk_index=row["chunk_index"],
            page_number=row["page_number"],
            user_id=row["user_id"],
            document_name=row.get("document_name", ""),
            file_type=row.get("file_type", ""),
        ))
    return chunks


async def retrieve(
    query_embedding: list[float],
    user_id: str,
    document_ids: Optional[list[str]] = None,
    top_k: int = 20,
    query: str = "",
) -> list[RetrievedChunk]:
    """
    Main entry point — async, returns hybrid-scored and neighbor-expanded chunks.
    """
    terms = _query_terms(query)
    significant = [t for t in terms if len(t) > 4]

    async with _new_session() as session:
        # Stage 1 — keyword-first: union results for ALL significant terms so that
        # multi-term queries aren't scored against only the first matching term.
        # We keep the row with the best (lowest) vector distance per chunk.
        emb_literal = _embedding_literal(query_embedding)
        merged_rows: dict[str, dict] = {}
        for term in significant:
            if document_ids and len(document_ids) == 1:
                where_clause = (
                    "de.user_id = CAST(:user_id AS uuid) "
                    "AND de.document_id = CAST(:doc_id AS uuid) "
                    "AND dc.text ILIKE :term"
                )
                params: dict = {
                    "user_id": user_id, "doc_id": document_ids[0],
                    "embedding": emb_literal, "top_k": top_k, "term": f"%{term}%",
                }
            elif document_ids:
                where_clause = (
                    "de.user_id = CAST(:user_id AS uuid) "
                    "AND de.document_id = ANY(CAST(:doc_ids AS uuid[])) "
                    "AND dc.text ILIKE :term"
                )
                params = {
                    "user_id": user_id, "doc_ids": document_ids,
                    "embedding": emb_literal, "top_k": top_k, "term": f"%{term}%",
                }
            else:
                where_clause = (
                    "de.user_id = CAST(:user_id AS uuid) "
                    "AND dc.text ILIKE :term"
                )
                params = {
                    "user_id": user_id, "embedding": emb_literal,
                    "top_k": top_k, "term": f"%{term}%",
                }

            result = await session.execute(
                sql_text(f"""
                    SELECT
                        de.chunk_id::text,
                        de.document_id::text,
                        de.user_id::text,
                        de.chunk_index,
                        de.page_number,
                        de.document_name,
                        de.file_type,
                        dc.text,
                        (de.embedding <=> CAST(:embedding AS vector)) AS distance
                    FROM document_embeddings de
                    JOIN document_chunks dc ON dc.id = de.chunk_id
                    WHERE {where_clause}
                    ORDER BY distance ASC
                    LIMIT :top_k
                """),
                params,
            )
            for row in [dict(r._mapping) for r in result.fetchall()]:
                cid = row["chunk_id"]
                if cid not in merged_rows or row["distance"] < merged_rows[cid]["distance"]:
                    merged_rows[cid] = row

        chunks: list[RetrievedChunk] = []
        if merged_rows:
            chunks = _rows_to_chunks(list(merged_rows.values()), terms)
            logger.info("Keyword-first stage matched %d chunks across %d terms", len(chunks), len(significant))

        # Stage 2 — fallback to pure semantic search
        if not chunks:
            logger.info("Keyword-first found nothing, falling back to semantic search")
            rows = await _semantic_search(session, query_embedding, user_id, document_ids, top_k)
            chunks = _rows_to_chunks(rows, terms)

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
            existing_indices = {c.chunk_index for c in doc_chunks}
            neighbor_indices: set[int] = set()
            for c in doc_chunks:
                if c.chunk_index > 0:
                    neighbor_indices.add(c.chunk_index - 1)
                neighbor_indices.add(c.chunk_index + 1)
            neighbor_indices -= existing_indices

            for n in await _fetch_neighbors(session, doc_id, user_id, list(neighbor_indices)):
                if n.chunk_id not in seen_ids:
                    neighbors.append(n)
                    seen_ids.add(n.chunk_id)

        logger.info("Expanded with %d neighbor chunks", len(neighbors))

    return chunks + sorted(neighbors, key=lambda c: c.chunk_index)
