# RAG Search — Changes & Architecture

This document describes all the changes made to `documents-rag` to add Elasticsearch hybrid search, Bedrock/Ollama provider switching, and a standalone Search + Ingest web UI.

---

## Table of Contents

1. [Overview](#overview)
2. [Provider Switching — Bedrock vs Ollama](#provider-switching)
3. [Elasticsearch Hybrid Search](#elasticsearch-hybrid-search)
4. [Search UI Service](#search-ui-service)
5. [Environment Variables](#environment-variables)
6. [Running the Stack](#running-the-stack)
7. [API Reference](#api-reference)
8. [File Map](#file-map)

---

## Overview

Three capabilities were added on top of the existing pipeline, **without modifying any existing service logic**:

| Capability | What changed |
|---|---|
| **Bedrock as default LLM/embed provider** | `rag_service/config.py`, `workers/config.py`, `.env` defaults |
| **Elasticsearch hybrid search** (BM25 + kNN + RRF) | New `es_retriever.py`, `es_indexer.py`, Jinja2 query templates, ES service in docker-compose |
| **Search UI** (`/search` + `/ingest`) | Entirely new `backend/search_ui/` service — zero existing files modified |

---

## Provider Switching

### Default: AWS Bedrock

The stack now defaults to Bedrock for both LLM generation and embeddings.

```env
LLM_PROVIDER=bedrock
EMBED_PROVIDER=bedrock
```

Models used:
- **Embeddings**: `amazon.titan-embed-text-v2:0` (1024-dim)
- **Generation**: `anthropic.claude-3-5-haiku-20241022-v1:0`

Required AWS env vars (in `.env`):
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...    # if using temporary credentials
```

### Optional: Ollama (local)

To run fully offline with Ollama, set the compose profile before starting:

```bash
COMPOSE_PROFILES=ollama docker compose up -d
```

And in `.env`:
```env
LLM_PROVIDER=ollama
EMBED_PROVIDER=ollama
```

The `ollama` and `ollama-init` services are gated behind the `ollama` profile and will not start unless `COMPOSE_PROFILES=ollama` is set.

---

## Elasticsearch Hybrid Search

### Architecture

```
Query
  │
  ├── BM25 (keyword)  ─── Elasticsearch ─── RRF fusion ──▶ ranked results
  └── kNN  (vector)   ───────────────────┘
```

Elasticsearch 8.13 is added as a sidecar to the existing pgvector pipeline. pgvector remains the source of truth — ES is a best-effort search layer.

### How documents reach ES

The **embedding worker** indexes chunks into ES immediately after writing them to pgvector:

```
Kafka (chunks.embedded) → embedding worker → pgvector (source of truth)
                                           → Elasticsearch (search layer, non-fatal)
```

If ES is down, the error is caught and logged — the pgvector write still succeeds.

### Index Mapping

Index name: `document_chunks` (configurable via `ES_INDEX_CHUNKS`)

| Field | Type | Purpose |
|---|---|---|
| `chunk_id` | keyword | Primary key |
| `document_id` | keyword | For scoping queries to a document set |
| `user_id` | keyword | Entitlement filter |
| `text` | text | BM25 full-text search |
| `document_name` | text | BM25 on document title |
| `embedding` | dense_vector (1024-dim) | kNN semantic search |
| `page_number` | integer | Metadata |
| `file_type` | keyword | Metadata |

### Search Modes

| Mode | Description | Endpoint param |
|---|---|---|
| `hybrid` (default) | BM25 + kNN fused with Reciprocal Rank Fusion | `"mode": "hybrid"` |
| `semantic` | Pure kNN cosine similarity | `"mode": "semantic"` |
| `keyword` | Pure BM25 (no embedding needed) | `"mode": "keyword"` |
| `pgvector` | Original pgvector path (fallback, always available) | `"mode": "pgvector"` |

### Query Templates

Jinja2 templates live in `backend/rag_service/migrations/templates/`:

- **`hybrid_search.jinja2`** — BM25 `bool/should` + `knn` block + `rank.rrf`
- **`semantic_search.jinja2`** — pure `knn` with filter
- **`keyword_search.jinja2`** — `bool/should` with `match` + `match_phrase` boosted

### Tuning Parameters (via env / config)

```env
ES_HYBRID_WINDOW=50      # RRF window_size — candidates considered per ranker
ES_HYBRID_RANK_CONSTANT=20  # RRF rank_constant — controls score distribution
ES_EMBEDDING_DIM=1024    # must match your embedding model output
```

### New Files

```
backend/rag_service/services/es_retriever.py       Async ES client — hybrid/semantic/keyword search
backend/rag_service/migrations/templates/
    hybrid_search.jinja2
    semantic_search.jinja2
    keyword_search.jinja2
backend/workers/shared/es_indexer.py               Bulk upsert + delete helpers
```

### Modified Files

```
backend/rag_service/config.py         Added ES settings, changed provider defaults
backend/rag_service/routers/query.py  Added SearchMode, routed hybrid/semantic/keyword → es_retriever
backend/rag_service/requirements.txt  Added elasticsearch[async]==8.13.0, jinja2
backend/workers/config.py             Added ES settings, changed provider defaults
backend/workers/embedding/consumer.py Added es_indexer.upsert_chunks() call after pgvector write
backend/workers/requirements.txt      Added elasticsearch[async]==8.13.0
docker-compose.yml                    Added elasticsearch service + elasticsearch_data volume
.env / .env.example                   Added ES vars, provider defaults
```

---

## Search UI Service

A completely standalone Flask service (`backend/search_ui/`) that adds two web UIs accessible via nginx. **No existing service code was modified.**

### Routes

| Route | Description |
|---|---|
| `GET /search` | Search UI — query documents with mode selector and result cards |
| `GET /ingest` | Ingest UI — upload files, add URLs, manage/delete documents |
| `POST /search-ui/api/search` | Proxies to `rag_service:8001/search` |
| `POST /search-ui/api/query` | Proxies to `rag_service:8001/query` (SSE streaming RAG answer) |
| `POST /search-ui/api/upload` | Proxies multipart upload to `api_gateway:8000/api/documents/upload` |
| `POST /search-ui/api/link` | Proxies URL ingestion to `api_gateway:8000/api/documents/link` |
| `GET /search-ui/api/documents` | Proxies to `api_gateway:8000/api/documents` |
| `DELETE /search-ui/api/documents/<id>` | Proxies to `api_gateway:8000/api/documents/<id>` |
| `GET /search-ui/health` | Health check — also pings rag_service |

### Search UI (`/search`)

- **Search** button — retrieves ranked document chunks, displayed as expandable cards showing score, file type, page number, document ID
- **Ask AI ✨** button — streams a full RAG answer via SSE, with source document tags
- Mode chips: Hybrid / Semantic / Keyword / pgvector
- Top K selector (5 / 10 / 20)
- User ID field (persisted in localStorage)

### Ingest UI (`/ingest`)

- **Upload File tab** — drag-and-drop or click-to-browse, multi-file, folder ID support, per-file status badges (Pending → Uploading → Processing / Failed)
- **Add URL tab** — submit a URL + optional title, gets queued for extraction
- **Manage tab** — lists all indexed documents with status, file type, size; delete by row button or by UUID input

### Environment Variables

```env
RAG_SERVICE_URL=http://rag_service:8001    # internal docker network
API_GATEWAY_URL=http://api_gateway:8000    # internal docker network
API_GW_TOKEN=                              # Bearer token if api_gateway auth is required
```

### New Files

```
backend/search_ui/
    app.py                Flask app — routes, proxy logic
    Dockerfile            python:3.11-slim + gunicorn
    requirements.txt      flask, flask-cors, requests, gunicorn
    templates/
        search.html       Search UI
        ingest.html       Ingest UI
```

### Docker Compose Changes

`search_ui` service added in `docker-compose.yml`:

```yaml
search_ui:
  build: ./backend/search_ui
  environment:
    RAG_SERVICE_URL: http://rag_service:8001
    API_GATEWAY_URL: http://api_gateway:8000
  depends_on:
    api_gateway: { condition: service_healthy }
    rag_service:  { condition: service_healthy }
  networks: [internal, public]
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/search-ui/health"]
```

### Nginx Changes

Three new location blocks added to `infrastructure/nginx/nginx.conf` — inserted **before** the catch-all `location /` that serves the React SPA:

```nginx
upstream search_ui {
    server search_ui:5000;
}

location = /search    { proxy_pass http://search_ui/search; }
location = /ingest    { proxy_pass http://search_ui/ingest; }
location /search-ui/  { proxy_pass http://search_ui/search-ui/;
                        proxy_buffering off; }  # SSE support
```

---

## Environment Variables

Full list of new variables added (all have defaults):

```env
# Provider
LLM_PROVIDER=bedrock          # bedrock | ollama
EMBED_PROVIDER=bedrock        # bedrock | ollama
COMPOSE_PROFILES=             # set to "ollama" to start Ollama containers

# AWS (required when using bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200
ES_INDEX_CHUNKS=document_chunks
ES_EMBEDDING_DIM=1024

# Search UI
API_GW_TOKEN=                 # Bearer token for api_gateway (leave blank if auth not enforced)
```

---

## Running the Stack

### Default (Bedrock)

```bash
# Set AWS credentials in .env, then:
docker compose up -d
```

### With Ollama (local, no AWS needed)

```bash
COMPOSE_PROFILES=ollama docker compose up -d
# First run pulls models — takes a few minutes
```

### Start only the Search UI (if stack already running)

```bash
docker compose up -d --build search_ui
docker exec documents-rag-nginx-1 nginx -s reload
```

### Access

| URL | Description |
|---|---|
| `http://localhost:8081/search` | Search UI |
| `http://localhost:8081/ingest` | Ingest / file upload UI |
| `http://localhost:8081` | Existing React frontend |
| `http://localhost:8082` | Kafka UI |
| `http://localhost:9091` | MinIO console |
| `http://localhost:9200` | Elasticsearch (direct, internal) |

---

## API Reference

### `POST /search` (rag_service)

```json
{
  "query": "how does autoscaling work?",
  "user_id": "admin@example.com",
  "document_ids": ["uuid1", "uuid2"],   // optional — scope to specific docs
  "top_k": 10,
  "mode": "hybrid"                       // hybrid | semantic | keyword | pgvector
}
```

Response:
```json
{
  "query": "...",
  "mode": "hybrid",
  "results": [
    {
      "chunk_id": "...",
      "document_id": "...",
      "text": "...",
      "score": 0.9231,
      "page_number": 3,
      "document_name": "autoscaler-runbook.pdf",
      "file_type": "pdf",
      "latency_ms": 42
    }
  ]
}
```

### `POST /query` (rag_service) — SSE stream

```json
{ "query": "...", "user_id": "..." }
```

SSE events:
```
data: {"type": "token", "token": "Based on "}
data: {"type": "token", "token": "the runbook..."}
data: {"type": "done",  "token": "", "sources": [...], "done": true}
```

---

## File Map

```
documents-rag/
├── backend/
│   ├── rag_service/
│   │   ├── config.py                          ← provider defaults + ES settings
│   │   ├── routers/query.py                   ← SearchMode routing added
│   │   ├── services/es_retriever.py           ★ NEW
│   │   └── migrations/templates/
│   │       ├── hybrid_search.jinja2           ★ NEW
│   │       ├── semantic_search.jinja2         ★ NEW
│   │       └── keyword_search.jinja2          ★ NEW
│   ├── workers/
│   │   ├── config.py                          ← provider defaults + ES settings
│   │   ├── embedding/consumer.py              ← ES indexing added
│   │   └── shared/es_indexer.py               ★ NEW
│   └── search_ui/                             ★ NEW (entire directory)
│       ├── app.py
│       ├── Dockerfile
│       ├── requirements.txt
│       └── templates/
│           ├── search.html
│           └── ingest.html
├── infrastructure/
│   └── nginx/nginx.conf                       ← search_ui upstream + 3 location blocks
├── docker-compose.yml                         ← elasticsearch + search_ui services
├── .env / .env.example                        ← new vars
└── rag-search.md                              ★ this file
```

`★ NEW` = entirely new file. Everything else = additive changes only.
