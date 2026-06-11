# Agent Evaluation Harness — Setup Guide

This guide walks you through running the evaluation harness that tests whether the Forge agent retrieves the right documents and produces correct, grounded answers.

---

## What Is This?

The harness is an automated evaluator (like [LangChain's agent harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness)) that:

1. Runs 6 pre-defined queries against a live agent
2. Captures the full run: plan steps, retrieved source types, final answer
3. Scores each run across three dimensions:
   - **Source Coverage** — did it search the right tools (Jira, Confluence, Slack, etc.)?
   - **Answer Faithfulness** — is the answer grounded in retrieved chunks?
   - **Answer Completeness** — does the answer mention expected facts?
4. Prints a pass/fail report per test case

---

## Prerequisites

### 1. Docker & Docker Compose
```bash
docker --version         # 24.x or later
docker compose version   # v2.x or later
```

### 2. Python 3.11+
```bash
python3 --version
```

### 3. AWS credentials (for Bedrock LLM judge)
The harness uses Claude Haiku to judge answer quality. You need AWS credentials with Bedrock access:
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
```
> **Skip this**: If you don't have AWS, use `--no-llm` flag to run with keyword-match scoring instead.

### 4. Harness Python packages
```bash
pip install httpx boto3 rich
```

---

## Step 1: Start the System

```bash
cd /path/to/documents-rag

# Copy environment file (first time only)
cp .env.example .env

# Start all services
docker compose up -d

# Wait until all services are healthy (~2–3 minutes)
docker compose ps
```

All services should show `healthy` before continuing. Key services to check:
- `api_gateway`, `rag_service`, `agent_service` — application layer
- `postgres`, `elasticsearch`, `kafka`, `minio` — infrastructure

---

## Step 2: Run Database Migrations + Create Admin User

Migrations run automatically on startup. Verify with:
```bash
docker compose exec api_gateway python -c "print('OK')"
```

Create the default admin users (first time only):
```bash
docker compose exec api_gateway python seed.py
```
This creates:
- `admin@example.com` / `changeme` — primary user
- `admin1@example.com` / `changeme` — service account

---

## Step 3: Seed Synthetic Documents

Upload the Forge SaaS test data (15 documents across two scenarios):

```bash
python scripts/seed_data.py --wait
```

The `--wait` flag polls until all documents reach `COMPLETED` status (embedding + indexing done). Typically takes 60–90 seconds.

Expected output:
```
Document                                    source_type  status     doc_id
────────────────────────────────────────────────────────────────────────
[seed] confluence-sop-notification-...     confluence   COMPLETED  abc123
[seed] jira-FRG-1001                       jira         COMPLETED  def456
[seed] slack-incidents-notification-...    slack        COMPLETED  ghi789
...
✓ 15/15 documents processed
```

**What gets seeded:**
- **Scenario A** (P1 Incident): Confluence SOP + post-mortem, 3 Jira tickets (FRG-1001/1002/1003), Slack #incidents thread, GitHub PR #55, HubSpot (Vertex Analytics)
- **Scenario B** (Feature): Confluence design doc + runbook, 2 Jira tickets (FRG-2001/2002), Slack #product-eng thread, GitHub PR #89, HubSpot (Meridian HR)

---

## Step 4: Create the Evaluation Agent

Open the agent builder UI at `http://localhost:8081/agents` and create an agent:

| Field | Value |
|---|---|
| **Name** | `Forge Incident Researcher` |
| **Description** | Cross-source researcher for the Forge platform |
| **System Prompt** | `You are a Forge engineering assistant. When investigating incidents or features, always search across all available sources: Jira for tickets, Confluence for documentation and SOPs, Slack for team discussions, GitHub for code changes, and HubSpot for customer impact. Synthesize findings into a clear, structured report.` |
| **Output Format** | Markdown |
| **Tools** | All (search_all) |

Or create via API:
```bash
curl -s -X POST http://localhost:8081/api/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8081/api/auth/login \
       -H 'Content-Type: application/json' \
       -d '{"email":"admin@example.com","password":"changeme"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')" \
  -d '{
    "name": "Forge Incident Researcher",
    "description": "Cross-source researcher for the Forge platform",
    "system_prompt": "You are a Forge engineering assistant. When investigating incidents or features, always search across all available sources: Jira for tickets, Confluence for documentation and SOPs, Slack for team discussions, GitHub for code changes, and HubSpot for customer impact. Synthesize findings into a clear, structured report.",
    "output_format": "markdown",
    "tools": ["search_all"]
  }'
```

Note the `id` field in the response — you will need it for the harness.

---

## Step 5: Run the Harness

```bash
# Full run with LLM judge (requires AWS creds)
python scripts/run_harness.py

# Fast run without LLM judge (keyword-match scoring)
python scripts/run_harness.py --no-llm

# Use a specific agent by ID
python scripts/run_harness.py --agent-id <uuid-from-step-4>

# Run only a subset of test cases
python scripts/run_harness.py --cases 1,3,5

# Save results to JSON
python scripts/run_harness.py --output results.json
```

---

## What the Harness Evaluates

Six test queries are run, each with a known "ground truth":

| # | Query | Expected Sources | Expected Facts |
|---|---|---|---|
| 1 | What happened during the notification outage? | jira, confluence, slack | FRG-1001, Vertex Analytics, circuit breaker |
| 2 | How do we respond to a notification service incident? | confluence | SOP, runbook, escalation |
| 3 | What is the fix status for the notification bug? | jira, github | FRG-1002, PR #55, merged |
| 4 | Which customers were impacted by the P1? | hubspot, slack | Vertex Analytics, enterprise |
| 5 | How does smart ticket routing work? | confluence, jira | ML classifier, FRG-2001, routing |
| 6 | What did the team decide about the routing rollout? | slack, confluence | feature flag, staged, Meridian HR |

### Scoring

| Dimension | Weight | Method |
|---|---|---|
| Source Coverage | 40% | Deterministic: fraction of expected sources retrieved |
| Answer Faithfulness | 30% | LLM judge: is the answer grounded in retrieved chunks? |
| Answer Completeness | 30% | LLM judge: does the answer mention expected facts? |

**Pass** = aggregate score ≥ 0.6. Target: **≥ 4/6 cases pass**.

---

## Example Output

```
┌──┬────────────────────────────────────────┬──────────┬───────────┬────────────┬───────────┬────────┐
│ # │ Query                                  │ Src Cov  │ Faithful  │ Complete   │ Aggregate │ Result │
├──┼────────────────────────────────────────┼──────────┼───────────┼────────────┼───────────┼────────┤
│ 1 │ What happened during the notif…        │ 1.00     │ 0.85      │ 0.90       │ 0.93      │ ✅ PASS│
│ 2 │ How do we respond to a notif…          │ 1.00     │ 0.90      │ 0.80       │ 0.90      │ ✅ PASS│
│ 3 │ What is the fix status for the…        │ 0.50     │ 0.75      │ 0.70       │ 0.65      │ ✅ PASS│
│ 4 │ Which customers were impacted…         │ 1.00     │ 0.80      │ 0.85       │ 0.88      │ ✅ PASS│
│ 5 │ How does smart ticket routing…         │ 1.00     │ 0.85      │ 0.75       │ 0.87      │ ✅ PASS│
│ 6 │ What did the team decide about…        │ 0.50     │ 0.60      │ 0.50       │ 0.53      │ ❌ FAIL│
├──┼────────────────────────────────────────┼──────────┼───────────┼────────────┼───────────┼────────┤
│   │ TOTAL (5/6 pass)                       │ 0.83     │ 0.79      │ 0.75       │ 0.79      │        │
└──┴────────────────────────────────────────┴──────────┴───────────┴────────────┴───────────┴────────┘
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Connection refused` on port 8081 | `docker compose up -d` and wait for healthy |
| `0 documents seeded` | Check `docker compose logs worker_embedding` for errors |
| Agent not found | Run Step 4 to create the agent; use `--agent-id` flag |
| All faithfulness scores = 0 | AWS creds missing or Bedrock not enabled; use `--no-llm` |
| Source coverage = 0 | Agent tools not set to `search_all`; check agent config |

---

## Resetting

```bash
# Delete seeded documents and re-seed
python scripts/seed_data.py --reset --wait

# Reset everything (nuclear)
docker compose down -v
docker compose up -d
# Then repeat Steps 2–5
```
