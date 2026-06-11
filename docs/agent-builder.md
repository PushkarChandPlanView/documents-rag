# Agent Builder

The agent builder lets users create saved, reusable research agents that automatically plan, search, synthesize, and upload results as documents.

---

## Architecture

```
browser (agent_ui:5001)
    ↓  HTTP proxy
agent_service:8002   ← FastAPI + LangGraph
    ↓  /search        ↓  /documents/upload
rag_service:8001    api_gateway:8000
    ↓
Elasticsearch
```

Two isolated services live in `backend/`:

| Service | Path | Port | Role |
|---|---|---|---|
| `agent_service` | `backend/agent_service/` | 8002 | FastAPI: agent CRUD + LangGraph execution |
| `agent_ui` | `backend/agent_ui/` | 5001 | Flask: web UI + HTTP proxy |

Neither service imports from existing services — all communication is over HTTP.

---

## Service: agent_service

### Directory layout

```
backend/agent_service/
  main.py                    FastAPI app entry point
  config.py                  Settings (Postgres, Bedrock, service URLs)
  db.py                      SQLAlchemy async engine + session factory
  alembic.ini
  alembic/
    env.py                   Uses separate version table: alembic_version_agent
    versions/
      001_agents.py          Creates agents + agent_runs tables
  models/
    agent.py                 Agent + AgentRun ORM models
  routers/
    agents.py                CRUD routes + /run SSE endpoint
  chains/
    agent_chain.py           LangGraph graph definition + run_agent()
  nodes/
    planner_node.py          Calls LLM → JSON list of steps
    tool_executor_node.py    Runs one step's ES search
    synthesizer_node.py      Assembles context, streams LLM answer
    uploader_node.py         Uploads result to api_gateway
  services/
    llm_client.py            Bedrock wrapper (generate + generate_stream)
    es_client.py             HTTP client → rag_service /search
    upload_client.py         HTTP client → api_gateway /documents/upload
```

### Database tables

**`agents`**
```sql
id            UUID PRIMARY KEY
user_id       VARCHAR(255)       -- identifies the owner (email or UUID)
name          VARCHAR(200)
description   TEXT
system_prompt TEXT               -- injected at synthesis time
output_format VARCHAR(20)        -- markdown | text | json
tools         JSONB              -- e.g. ["search_jira", "search_confluence"]
created_at    TIMESTAMPTZ
updated_at    TIMESTAMPTZ
```

**`agent_runs`**
```sql
id                 UUID PRIMARY KEY
agent_id           UUID REFERENCES agents(id)
user_id            VARCHAR(255)
query              TEXT
status             VARCHAR(20)    -- running | completed | failed
plan               JSONB          -- list of step strings from planner
result_document_id VARCHAR(255)   -- document_id from api_gateway after upload
created_at         TIMESTAMPTZ
completed_at       TIMESTAMPTZ
```

### API routes

```
GET    /health
POST   /agents                  create agent
GET    /agents?user_id=…        list agents for a user
GET    /agents/{id}             get agent detail
PATCH  /agents/{id}             update agent fields
DELETE /agents/{id}             delete agent + all runs
POST   /agents/{id}/run         start a run → SSE stream
GET    /agents/runs/{run_id}    get run status + result_document_id
```

### LangGraph execution graph

```
START
  │
  ▼
planner_node          LLM produces a JSON array of 3–6 step strings
  │
  ▼ (conditional loop)
tool_executor_node    Runs one step at a time:
  │                     • detects source keyword in step text (jira/confluence/slack/…)
  │                     • calls rag_service /search with source_types filter
  │                     • appends chunk results to step_results
  │                     • increments current_step
  │
  ├── (more steps?) ──→ tool_executor_node
  │
  ▼
synthesizer_node      Dedupes chunks, builds context, streams LLM answer
  │
  ▼
uploader_node         Uploads answer as .txt to api_gateway (source_type="agent")
  │
  ▼
END
```

**Source-type keyword detection** (in `tool_executor_node.py`):

| Keyword in step text | ES filter applied |
|---|---|
| `jira` | `source_types: ["jira"]` |
| `confluence` | `source_types: ["confluence"]` |
| `slack` | `source_types: ["slack"]` |
| `github` | `source_types: ["github"]` |
| `hubspot` | `source_types: ["hubspot"]` |
| `url` | `source_types: ["url"]` |
| `upload` | `source_types: ["upload"]` |
| *(none)* | no filter — searches all sources |

### SSE event stream

The `/agents/{id}/run` endpoint streams SSE events. Each `data:` line is a JSON object:

```
data: {"type": "plan",       "steps": ["Search Jira for…", "Search Confluence for…"]}
data: {"type": "step_done",  "step": 0, "step_text": "Search Jira for…", "chunks_found": 7}
data: {"type": "step_done",  "step": 1, "step_text": "Search Confluence for…", "chunks_found": 4}
data: {"type": "generating"}
data: {"type": "token",      "content": "## Summary\n\n"}
data: {"type": "token",      "content": "Based on the Jira tickets…"}
...
data: {"type": "uploaded",   "document_id": "abc123-…"}
data: {"type": "done",       "document_id": "abc123-…"}
```

On error:
```
data: {"type": "error", "content": "Agent execution failed: …"}
```

### Output formats

| Format | Behavior |
|---|---|
| `markdown` | LLM responds with headers, bullet points, code blocks |
| `text` | LLM responds in plain prose, no Markdown |
| `json` | LLM responds with a single valid JSON object |

---

## Service: agent_ui

### Directory layout

```
backend/agent_ui/
  app.py              Flask app + proxy routes
  Dockerfile
  requirements.txt
  templates/
    agents.html       Full UI: agent list, create/edit drawer, run panel
```

### Proxy routes

All routes under `/agent-ui/` are thin proxies to `agent_service`:

```
GET  /agents                        → renders agents.html
GET  /agent-ui/health
GET  /agent-ui/api/agents           → agent_service GET /agents
POST /agent-ui/api/agents           → agent_service POST /agents
PATCH  /agent-ui/api/agents/<id>    → agent_service PATCH /agents/{id}
DELETE /agent-ui/api/agents/<id>    → agent_service DELETE /agents/{id}
POST /agent-ui/api/agents/<id>/run  → agent_service POST /agents/{id}/run  (SSE)
GET  /agent-ui/api/runs/<run_id>    → agent_service GET /agents/runs/{run_id}
```

---

## Configuration

### Environment variables (agent_service)

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_URL` | `postgresql+asyncpg://docstore:changeme@postgres:5432/docstore` | Shared Postgres instance |
| `RAG_SERVICE_URL` | `http://rag_service:8001` | Used by es_client for /search |
| `API_GATEWAY_URL` | `http://api_gateway:8000` | Used by upload_client |
| `GW_SERVICE_EMAIL` | `admin1@example.com` | Service account for api_gateway auth |
| `GW_SERVICE_PASS` | `changeme` | Service account password |
| `AWS_REGION` | `us-east-1` | Bedrock region |
| `AWS_ACCESS_KEY_ID` | — | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | — | AWS credentials |
| `BEDROCK_LLM_MODEL` | `us.anthropic.claude-opus-4-5-20251101-v1:0` | Bedrock model for planning + synthesis |

### Environment variables (agent_ui)

| Variable | Default | Description |
|---|---|---|
| `AGENT_SERVICE_URL` | `http://agent_service:8002` | agent_service base URL |

---

## Deployment

### First-time setup

```bash
# 1. Build and start services
docker compose build agent_service agent_ui
docker compose up -d agent_service

# 2. Run the migration (separate version table: alembic_version_agent)
docker compose exec agent_service alembic upgrade head

# 3. Start agent_ui and reload nginx
docker compose up -d agent_ui nginx
```

### Subsequent deploys

```bash
docker compose build agent_service agent_ui
docker compose up -d agent_service agent_ui
# If alembic migrations added:
docker compose exec agent_service alembic upgrade head
```

---

## Usage

### Access the UI

Open **http://localhost:8081/agents**

### Creating an agent

1. Click **+ New Agent**
2. Fill in:
   - **Name** — e.g. "Incident Researcher"
   - **Description** — what it does (optional)
   - **System Prompt** — instructs the LLM on tone, depth, and domain
   - **Output Format** — Markdown / Plain Text / JSON
   - **Tools** — which sources to search (All Sources, Jira, Confluence, Slack, GitHub, HubSpot)
3. Click **Save Agent**

### Running an agent

1. Click **▶ Run** on any agent card
2. Type a query in the run panel (e.g. "Summarize all P0 incidents from Q1 2026")
3. Watch the live plan checklist and streamed answer
4. When done, the result is automatically saved as a searchable document (visible in **Ingest → Manage** tab)

### Via API

```bash
# Create an agent
curl -X POST http://localhost:8081/agent-ui/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "you@example.com",
    "name": "Jira Researcher",
    "system_prompt": "You are a technical writer. Research and produce a Markdown report.",
    "output_format": "markdown",
    "tools": ["search_jira", "search_confluence"]
  }'

# List agents
curl "http://localhost:8081/agent-ui/api/agents?user_id=you@example.com"

# Run an agent (streaming)
curl -N -X POST http://localhost:8081/agent-ui/api/agents/<agent_id>/run \
  -H "Content-Type: application/json" \
  -d '{"query": "P0 incidents last quarter", "user_id": "you@example.com"}'

# Get run status
curl http://localhost:8081/agent-ui/api/runs/<run_id>
```

---

## How it differs from agentic search

| | `/agentic-query` (rag_service) | Agent Builder |
|---|---|---|
| Saved? | No — one-shot | Yes — reusable named agent |
| System prompt | Fixed in code | User-defined per agent |
| Output format | Markdown only | Markdown / Text / JSON |
| Persistence | Not stored | Run history in `agent_runs` table |
| Result | Streamed to browser | Uploaded as a document |
| Source routing | LangGraph router node | Keyword detection from planner steps |
| Use case | Ad-hoc deep search | Repeatable research workflows |

---

## Adding a new tool / source type

1. Add the keyword mapping in `nodes/tool_executor_node.py`:
   ```python
   _SOURCE_KEYWORDS = {
       ...
       "notion": ["notion"],   # new source
   }
   ```

2. Ingest documents with `source_type="notion"` (via `POST /api/documents/upload` with `source_type` field)

3. The agent will automatically route steps mentioning "notion" to that source filter

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `GET /agents` returns 502 | `docker compose logs agent_ui` — agent_service may be unhealthy |
| Migration fails with "Can't locate revision" | `docker compose exec agent_service alembic current` — must use `alembic_version_agent` table |
| Planner returns no steps | Check Bedrock credentials in `.env`; see `docker compose logs agent_service` |
| Upload step fails silently | Check `GW_SERVICE_EMAIL`/`GW_SERVICE_PASS` match a valid api_gateway account |
| 405 on POST after nginx restart | `docker compose restart nginx` — nginx must reload the `agent_ui` upstream |
