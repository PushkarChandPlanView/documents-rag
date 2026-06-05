# Document Intelligence Platform

A fully self-hosted AI document storage, search, and summarization platform. Upload PDFs, DOCX, or TXT files and get automatic text extraction, semantic search, and AI-powered Q&A — all running locally with no cloud API calls.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Browser (localhost:8081)                                               │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │ HTTP / WebSocket
┌─────────────────────▼───────────────────────────────────────────────────┐
│  Nginx  (reverse proxy, port 8081)                                      │
│  /api/*  → api_gateway:8000                                             │
│  /ws/*   → api_gateway:8000  (WebSocket upgrade)                        │
│  /*      → frontend:80       (React SPA)                                │
└──────────────┬──────────────────────────────┬──────────────────────────┘
               │ REST / WS                    │ static assets
┌──────────────▼──────────────┐  ┌────────────▼──────────────────────────┐
│  api_gateway  (FastAPI)      │  │  frontend  (React + Vite)             │
│  - JWT auth                  │  │  - React Query, Zustand               │
│  - document upload           │  │  - @planview/pv-uikit                 │
│  - WebSocket status feed     │  └───────────────────────────────────────┘
│  - proxies chat → rag_svc    │
└──────┬──────────┬────────────┘
       │          │
       │ Kafka    │ SQL
       │          ▼
       │  ┌──────────────┐   ┌──────────────┐
       │  │  PostgreSQL   │   │    MinIO     │
       │  │  (metadata,   │   │ (raw files + │
       │  │   chunks,     │   │  extracted   │
       │  │   job status) │   │   text)      │
       │  └──────────────┘   └──────────────┘
       │
       │  Kafka Pipeline (event-driven, async)
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  [document_uploaded]                                                     │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────┐   reads/writes MinIO, PostgreSQL               │
│  │  text_extraction ×2 │──────────────────────────────►                 │
│  └──────────┬──────────┘                                                │
│             │ [text_extracted]                                           │
│             ▼                                                            │
│  ┌─────────────────────┐   writes chunks → PostgreSQL                   │
│  │  chunking       ×2  │──────────────────────────────►                 │
│  └──────────┬──────────┘                                                │
│             │ [document_chunked]                                         │
│             ▼                                                            │
│  ┌─────────────────────┐   reads PostgreSQL, writes ChromaDB            │
│  │  embedding      ×2  │──────── Ollama (nomic-embed-text) ────────►    │
│  └──────────┬──────────┘                                                │
│             │ [embeddings_generated]                                     │
│             ▼                                                            │
│  ┌─────────────────────┐   reads PostgreSQL, writes summary             │
│  │  summarization  ×1  │──────── Ollama (llama3) ────────────────►      │
│  └──────────┬──────────┘                                                │
│             │ [summary_generated]                                        │
│             ▼                                                            │
│       PostgreSQL (document.status = COMPLETED)                          │
│       WebSocket → browser (pipeline stage updates)                      │
│                                                                          │
│  On error at any stage → [dlq.document_errors]                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  RAG / Chat Query Flow                                                   │
│                                                                          │
│  Browser ──POST /api/chat──► api_gateway ──► rag_service (internal)     │
│                                                    │                     │
│                                    embed query ────► Ollama              │
│                                    cosine search ──► ChromaDB (top 20)  │
│                                    rerank ──────────► top 5 chunks       │
│                                    build context + prompt                │
│                                    stream ──────────► Ollama (llama3)   │
│                                                    │                     │
│  Browser ◄── SSE token stream ◄── api_gateway ◄───┘                    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Services

| Service | Image / Build | Port | Role |
|---|---|---|---|
| `nginx` | `nginx:alpine` | **8081** (host) | Reverse proxy |
| `frontend` | `./frontend` | 80 (internal) | React SPA |
| `api_gateway` | `./backend/api_gateway` | 8000 (internal) | REST API + WebSocket |
| `rag_service` | `./backend/rag_service` | 8001 (internal) | Semantic search + chat |
| `worker_text_extraction` | `./backend/workers` | — | PDF/DOCX/TXT extraction |
| `worker_chunking` | `./backend/workers` | — | Text splitting |
| `worker_embedding` | `./backend/workers` | — | Vector generation |
| `worker_summarization` | `./backend/workers` | — | AI summarization |
| `postgres` | `postgres:16-alpine` | 5432 (internal) | Relational data |
| `kafka` | `confluentinc/cp-kafka:7.6.0` | 9092 (internal) | Event streaming |
| `zookeeper` | `confluentinc/cp-zookeeper:7.6.0` | 2181 (internal) | Kafka coordination |
| `chroma` | `chromadb/chroma:0.5.0` | 8000 (internal) | Vector store |
| `minio` | `minio/minio:latest` | **9091** (console) | Object storage |
| `ollama` | `ollama/ollama:latest` | 11434 (internal) | Local LLM inference |

> `rag_service` is on the `internal` Docker network only — never exposed through Nginx.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [OrbStack](https://orbstack.dev/)
- 16 GB RAM recommended (Ollama + all workers)
- ~15 GB disk for Ollama models (llama3 + nomic-embed-text)

---

## Quick Start

### 1. Clone and start

```bash
git clone <repo-url>
cd document-summarizer

make up        # copies .env.example → .env, starts all containers
make migrate   # runs Alembic database migrations
make seed      # creates admin@example.com / changeme
```

### 2. Pull AI models (takes 5–15 min depending on connection)

```bash
make pull-models   # downloads llama3 + nomic-embed-text into Ollama
```

### 3. Open the UI

```
http://localhost:8081
```

Log in with `admin@example.com` / `changeme`.

---

## Environment Variables

Copy `.env.example` to `.env` (done automatically by `make up`) and adjust as needed.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `changeme` | Database password |
| `JWT_SECRET_KEY` | *(set a strong value in prod)* | Signs JWT tokens |
| `OLLAMA_LLM_MODEL` | `llama3` | LLM for summarization and chat |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `MAX_UPLOAD_SIZE_MB` | `100` | Max file upload size |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Allowed frontend origins |

---

## Development Workflow

### Backend (API gateway)

```bash
make shell-api          # bash inside api_gateway container
make migrate            # run new Alembic migrations
make logs svc=api_gateway
```

### Workers

Each worker runs from the same `./backend/workers` image, selected by `WORKER_TYPE` env var. To tail a specific worker:

```bash
make logs svc=worker_text_extraction
make logs svc=worker_embedding
```

### Frontend (local dev server, hot reload)

```bash
make frontend-install   # pnpm install
make frontend-dev       # starts Vite dev server on :5173
```

The dev server proxies `/api` and `/ws` to the containerised api_gateway, so you can run the frontend locally while keeping the backend in Docker.

### Database

```bash
make shell-db           # opens psql
```

Useful queries:

```sql
-- Check pipeline progress
SELECT filename, status, updated_at FROM documents ORDER BY created_at DESC;

-- Inspect processing jobs per document
SELECT d.filename, pj.stage, pj.status, pj.error_message
FROM processing_jobs pj JOIN documents d ON d.id = pj.document_id
ORDER BY pj.created_at DESC;

-- Count stored vector chunks
SELECT document_id, COUNT(*) FROM document_chunks GROUP BY document_id;
```

---

## Make Targets

```
make up                 Start all services
make down               Stop all services
make build              Rebuild all Docker images (no cache)
make migrate            Run Alembic migrations
make seed               Create default admin user
make pull-models        Pull Ollama AI models
make logs               Tail all logs  (make logs svc=api_gateway for one)
make restart            Restart a service  (make restart svc=worker_embedding)
make ps                 Show container status
make shell-api          Bash shell in api_gateway container
make shell-db           psql shell in postgres container
make test               Run integration tests
make clean              Remove all containers, volumes, and local images
make frontend-install   Install frontend dependencies (pnpm)
make frontend-dev       Run frontend dev server locally
```

---

## Document Processing Pipeline

```
Upload (PDF/DOCX/TXT, max 100 MB)
  │
  ├─► MinIO (raw file stored)
  ├─► PostgreSQL (Document row, status=PENDING)
  └─► Kafka: document_uploaded
            │
            ▼
      text_extraction worker
        - PDF  → PyMuPDF + pdfplumber
        - DOCX → python-docx
        - TXT  → direct read
        - Extracted text → MinIO
        - status → PROCESSING
            │
            ▼ Kafka: text_extracted
            │
      chunking worker
        - RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
        - Docs > 50k chars → semantic/sentence-boundary chunking
        - Chunks → PostgreSQL (document_chunks table)
            │
            ▼ Kafka: document_chunked
            │
      embedding worker
        - Fetches chunks from PostgreSQL
        - Batches of 32 → Ollama /api/embeddings (nomic-embed-text)
        - Vectors + metadata → ChromaDB
            │
            ▼ Kafka: embeddings_generated
            │
      summarization worker
        - ≤ 8k tokens  → single-pass prompt to Ollama (llama3)
        - > 8k tokens  → map-reduce (chunk summaries → final summary)
        - Summary → PostgreSQL (documents.summary)
        - status → COMPLETED
            │
            ▼ Kafka: summary_generated
            │
      WebSocket notification → browser (pipeline stepper updates)
```

### Processing time estimates

| Stage | Typical duration |
|---|---|
| Upload + extraction | 2–15s |
| Chunking | 1–5s |
| Embedding (CPU) | 30s–3min |
| Summarization (CPU, llama3) | 1–10min |

> First request after startup: add ~60s for Ollama to load the model into memory.

---

## Project Structure

```
document-summarizer/
├── backend/
│   ├── api_gateway/
│   │   ├── main.py            FastAPI app + lifespan
│   │   ├── config.py          Pydantic Settings
│   │   ├── dependencies.py    get_db, get_current_user
│   │   ├── routers/           auth, documents, chat, health
│   │   ├── services/          auth, document, storage, kafka_producer
│   │   ├── models/            SQLAlchemy ORM models
│   │   ├── schemas/           Pydantic request/response schemas
│   │   └── alembic/           DB migrations
│   ├── workers/
│   │   ├── worker_runner.py   Entry point (reads WORKER_TYPE)
│   │   ├── base/              BaseConsumer, BaseProducer (retry, DLQ)
│   │   ├── text_extraction/   PDF/DOCX/TXT extractors
│   │   ├── chunking/          RecursiveCharacter + semantic strategies
│   │   ├── embedding/         Ollama batch embedder
│   │   ├── summarization/     single_pass + map_reduce strategies
│   │   └── shared/            db_client, minio_client, chroma_client, schemas
│   └── rag_service/
│       ├── main.py            Internal FastAPI (port 8001)
│       ├── chains/            rag_chain (LCEL: retrieve→rerank→stream)
│       ├── services/          retriever, llm_client, context_builder
│       ├── routers/           query (SSE), search, health
│       └── utils/             prompt_templates
├── frontend/
│   └── src/
│       ├── api/               axios client, auth/documents/chat/search
│       ├── auth/              AuthProvider, ProtectedRoute
│       ├── components/        Layout, DocumentUpload, ChatWindow, SearchBar
│       ├── hooks/             useDocuments, useUpload, useWebSocket
│       ├── pages/             Login, Dashboard, Documents, Search, Chat
│       └── store/             queryClient, authStore (Zustand)
└── infrastructure/
    ├── nginx/nginx.conf
    ├── postgres/init.sql
    ├── kafka/create-topics.sh
    ├── minio/init-buckets.sh
    └── ollama/pull-models.sh
```
