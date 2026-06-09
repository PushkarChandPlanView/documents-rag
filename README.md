# Document Intelligence Platform

A fully self-hosted AI document storage, search, summarization, and compliance platform. Upload PDFs, DOCX, images, or web links and get automatic text extraction, semantic search, AI-powered Q&A, and compliance checks — running locally with Ollama or against AWS Bedrock.

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
│  - document upload / links   │  │  - @planview/pv-uikit                 │
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
       │  │  embeddings   │   │   text)      │
       │  │  [pgvector])  │   │              │
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
│  ┌─────────────────────┐   reads PostgreSQL, writes pgvector            │
│  │  embedding      ×2  │──────── Ollama or Bedrock ──────────►          │
│  └──────────┬──────────┘                                                │
│             │ [embeddings_generated]                                     │
│             ▼                                                            │
│  ┌─────────────────────┐   reads PostgreSQL, writes summary             │
│  │  summarization  ×2  │──────── Ollama or Bedrock ──────────►          │
│  └──────────┬──────────┘                                                │
│             │ [summary_generated]                                        │
│             ▼                                                            │
│  ┌─────────────────────┐   runs active compliance rules                 │
│  │  compliance     ×1  │──────── Ollama or Bedrock (LLM rules) ────►    │
│  └──────────┬──────────┘                                                │
│             │                                                            │
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
│                                    embed query ────► Ollama or Bedrock  │
│                                    cosine search ──► pgvector (top 20)  │
│                                    rerank ──────────► top 5 chunks       │
│                                    build context + prompt                │
│                                    stream ──────────► Ollama or Bedrock │
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
| `worker_text_extraction` | `./backend/workers` | — | Extraction (PDF/DOCX/XLSX/PPTX/images/web) ×2 |
| `worker_chunking` | `./backend/workers` | — | Text splitting ×2 |
| `worker_embedding` | `./backend/workers` | — | Vector generation ×2 |
| `worker_summarization` | `./backend/workers` | — | AI summarization ×2 |
| `worker_compliance` | `./backend/workers` | — | Compliance rule checks ×1 |
| `postgres` | `pgvector/pgvector:pg16` | 5432 (internal) | Relational data + vector store |
| `kafka` | `confluentinc/cp-kafka:7.6.0` | 9092 (internal) | Event streaming |
| `zookeeper` | `confluentinc/cp-zookeeper:7.6.0` | 2181 (internal) | Kafka coordination |
| `minio` | `minio/minio:latest` | **9091** (console) | Object storage |
| `ollama` | `ollama/ollama:latest` | 11434 (internal) | Local LLM inference (optional) |

> `rag_service` is on the `internal` Docker network only — never exposed through Nginx.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [OrbStack](https://orbstack.dev/)
- **Ollama mode:** 16 GB RAM recommended (~8 GB for Ollama + workers)
- **Bedrock mode:** 8 GB RAM sufficient (no local model inference)
- ~10 GB disk if using Ollama models

---

## Quick Start

### 1. Clone and start

```bash
git clone <repo-url>
cd document-summarizer

make up        # copies .env.example → .env, starts all containers
make migrate   # runs Alembic database migrations (also runs automatically on startup)
make seed      # creates admin@example.com / changeme
```

### 2. Configure LLM provider

**Option A — Ollama (local, no cloud)**

```bash
make pull-models   # downloads qwen3:4b + mxbai-embed-large into Ollama
```

Models are set in `.env`:
```bash
LLM_PROVIDER=ollama
EMBED_PROVIDER=ollama
OLLAMA_LLM_MODEL=qwen3:4b
OLLAMA_EMBED_MODEL=mxbai-embed-large
```

**Option B — AWS Bedrock**

Fill in your AWS credentials in `.env` and switch the providers:
```bash
LLM_PROVIDER=bedrock
EMBED_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_SESSION_TOKEN=<optional, for SSO/assumed roles>
BEDROCK_LLM_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_EMBED_MODEL=amazon.titan-embed-text-v2:0
```

> Note: newer Claude models on Bedrock require a cross-region inference profile prefix (`us.`, `eu.`, or `ap.`).

Then restart the affected services:
```bash
docker compose up -d worker_embedding worker_summarization worker_compliance rag_service
```

### 3. Open the UI

```
http://localhost:8081
```

Log in with `admin@example.com` / `changeme`.

---

## Environment Variables

Copy `.env.example` to `.env` (done automatically by `make up`) and adjust as needed.

### LLM / Embedding provider

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` or `bedrock` |
| `EMBED_PROVIDER` | `ollama` | `ollama` or `bedrock` (can differ from `LLM_PROVIDER`) |

### Ollama

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_LLM_MODEL` | `qwen3:4b` | LLM for summarization, chat, and compliance |
| `OLLAMA_EMBED_MODEL` | `mxbai-embed-large` | Embedding model (1024 dims) |
| `OLLAMA_NUM_CTX` | `4096` | Context window size |

### AWS Bedrock

| Variable | Default | Description |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `AWS_ACCESS_KEY_ID` | — | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | — | AWS secret key |
| `AWS_SESSION_TOKEN` | — | Optional, for SSO / assumed roles |
| `BEDROCK_LLM_MODEL` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | LLM model ID |
| `BEDROCK_EMBED_MODEL` | `amazon.titan-embed-text-v2:0` | Embedding model ID (1024 dims) |

### General

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `changeme` | Database password |
| `JWT_SECRET_KEY` | *(set a strong value in prod)* | Signs JWT tokens |
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
make logs svc=worker_compliance
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
SELECT name, status, updated_at FROM documents ORDER BY created_at DESC;

-- Inspect processing jobs per document
SELECT d.name, pj.stage, pj.status, pj.error_message
FROM processing_jobs pj JOIN documents d ON d.id = pj.document_id
ORDER BY pj.created_at DESC;

-- Count stored vector chunks
SELECT document_id, COUNT(*) FROM document_embeddings GROUP BY document_id;
```

---

## Make Targets

```
make up                 Start all services
make down               Stop all services
make build              Rebuild all Docker images (no cache)
make migrate            Run Alembic migrations
make seed               Create default admin user (admin@example.com / changeme)
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
Upload (PDF/DOCX/XLSX/PPTX/images/web links, max 100 MB)
  │
  ├─► MinIO (raw file stored)
  ├─► PostgreSQL (Document row, status=PENDING)
  └─► Kafka: document_uploaded
            │
            ▼
      text_extraction worker
        - PDF      → PyMuPDF + pdfplumber
        - DOCX     → python-docx
        - XLSX     → openpyxl
        - PPTX     → python-pptx
        - Images   → Tesseract OCR
        - Web links → fetch + HTML strip
        - Extracted text → MinIO
            │
            ▼ Kafka: text_extracted
            │
      chunking worker
        - Token-based chunking (512 tokens, 64 overlap — cl100k_base)
        - Docs > 50k chars → semantic/sentence-boundary chunking
        - Chunks → PostgreSQL (document_chunks table)
            │
            ▼ Kafka: document_chunked
            │
      embedding worker
        - Fetches chunks from PostgreSQL
        - Contextual prefix per chunk (doc name + position) for better retrieval
        - Batch embed → Ollama or Bedrock
        - Vectors + metadata → PostgreSQL (pgvector, 1024 dims)
            │
            ▼ Kafka: embeddings_generated
            │
      summarization worker
        - ≤ 12k tokens → single-pass prompt
        - > 12k tokens → map-reduce (batch summaries → final summary)
        - Summary → PostgreSQL (document_summaries, versioned)
        - status → COMPLETED
            │
            ▼ Kafka: summary_generated
            │
      compliance worker
        - Runs all active compliance rules against the document
        - Rule types: keyword_required, keyword_forbidden, age_limit_days, llm_check
        - Results → PostgreSQL (compliance_rule_results)
            │
            ▼
      WebSocket notification → browser (pipeline stepper updates)
```

### Processing time estimates

| Stage | Ollama (CPU) | Bedrock |
|---|---|---|
| Upload + extraction | 2–15s | 2–15s |
| Chunking | 1–5s | 1–5s |
| Embedding | 30s–3min | 2–10s |
| Summarization | 1–10min | 5–30s |
| Compliance | 30s–5min | 5–20s |

---

## Project Structure

```
document-summarizer/
├── backend/
│   ├── api_gateway/
│   │   ├── main.py            FastAPI app + lifespan
│   │   ├── config.py          Pydantic Settings
│   │   ├── dependencies.py    get_db, get_current_user
│   │   ├── routers/           auth, documents, chat, search, compliance, health
│   │   ├── services/          auth, document, storage, kafka_producer, seed_compliance
│   │   ├── models/            SQLAlchemy ORM models
│   │   ├── schemas/           Pydantic request/response schemas
│   │   └── alembic/           DB migrations
│   ├── workers/
│   │   ├── worker_runner.py   Entry point (reads WORKER_TYPE)
│   │   ├── base/              BaseConsumer, BaseProducer (retry, DLQ)
│   │   ├── text_extraction/   Multi-format extractors
│   │   ├── chunking/          Token-based + semantic strategies
│   │   ├── embedding/         Batch embedder with contextual prefix
│   │   ├── summarization/     single_pass + map_reduce strategies
│   │   ├── compliance/        Rule engine + consumer
│   │   └── shared/            db_client, minio_client, pgvector_client
│   │       └── providers/     llm_factory, ollama, bedrock
│   └── rag_service/
│       ├── main.py            Internal FastAPI (port 8001)
│       ├── services/          retriever, llm_client, context_builder
│       │   └── providers/     ollama, bedrock
│       ├── routers/           query (SSE), search, health
│       └── utils/             prompt_templates
├── frontend/
│   └── src/
│       ├── api/               axios client, auth/documents/chat/search/compliance
│       ├── components/        Layout, documents, compliance, chat, search
│       ├── hooks/             useDocuments, useUpload, useWebSocket, useCompliance
│       ├── pages/             Login, Dashboard, Documents
│       └── store/             queryClient, authStore (Zustand)
└── infrastructure/
    ├── nginx/nginx.conf
    ├── postgres/init.sql
    ├── kafka/create-topics.sh
    ├── minio/init-buckets.sh
    └── ollama/pull-models.sh
```
