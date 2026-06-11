# Plan: Folder Email Webhook → Document Generation

## Context
Each folder should have a dedicated email address. When an email is sent to it, a new document is generated inside that folder using the email subject + body as the LLM prompt, then fed through the standard processing pipeline (chunking → embedding → summarization → compliance).

---

## Dev Email Setup — Cloudmailin (no domain needed)

**Cloudmailin** provides an instant inbound email address with no domain ownership required.

Setup steps:
1. Sign up at [cloudmailin.com](https://cloudmailin.com) → free tier
2. Create a "Target" → set webhook URL to `https://<ngrok-url>/api/webhooks/email`
3. Set format to **JSON** (default)
4. You get an address like `abc123@cloudmailin.net`

**Folder addressing** — Cloudmailin supports `+` sub-addressing:
```
abc123+folder-{uuid}@cloudmailin.net   ← dev (one Cloudmailin account, all folders)
folder-{uuid}@yourdomain.com           ← production (per-folder address)
```

Both formats embed the UUID → same regex extracts it.

---

## Email Address Format

The UUID is always embedded in the local part before `@`:

| Environment | Format | Example |
|---|---|---|
| Dev (Cloudmailin) | `{base}+folder-{uuid}@cloudmailin.net` | `abc123+folder-550e8400...@cloudmailin.net` |
| Production | `folder-{uuid}@{WEBHOOK_EMAIL_DOMAIN}` | `folder-550e8400...@mail.acme.com` |

Extraction regex: `folder-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})`  
This matches both formats — no DB column or migration needed.

---

## Config — `backend/api_gateway/config.py`

New settings:
```python
webhook_email_domain: str = "mail.localhost"   # production domain
webhook_secret: str = ""                       # HMAC verification (empty = skip)
email_provider: str = "cloudmailin"            # cloudmailin | mailgun | postmark | generic
```

---

## End-to-End Flow
```
User sends email to folder-{uuid} address
        │
        ▼
Cloudmailin / provider POSTs to  POST /api/webhooks/email
        │
        ├─ Provider adapter normalises payload → {to, subject, body, in_reply_to}
        ├─ Regex: extract folder_id from `to`
        ├─ Skip if in_reply_to present  (only root email triggers generation)
        ├─ validate folder exists + get owner user_id
        ├─ prompt = f"{subject}\n\n{body}"
        ├─ GenerationService.generate_text(prompt) → content str
        ├─ storage_service.upload_file(content, bucket="documents-raw", key="{doc_id}/email.txt")
        ├─ create_document_item(db, user_id, filename=subject, mime_type="text/plain", parent_id=folder_id)
        └─ kafka_producer.publish(DocumentUploadedEvent) → normal pipeline
```

---

## Files to Create

### 1. `backend/api_gateway/services/generation_service.py`  *(new)*
```python
async def generate_text(prompt: str, settings) -> str
```
- Reads `settings.llm_provider` → calls Ollama or Bedrock
- **Ollama**: `POST {ollama_base_url}/api/generate` via `httpx.AsyncClient`  
  (model=`settings.ollama_llm_model`, temperature=`settings.ollama_temperature`, stream=False)
- **Bedrock**: `boto3` `invoke_model_with_response_stream` — same pattern as `workers/shared/providers/bedrock.py`
- No new deps — `httpx` already in api_gateway requirements; boto3 already available

### 2. `backend/api_gateway/routers/webhooks.py`  *(new)*
```
POST /api/webhooks/email
```
**Provider adapters** (selected by `settings.email_provider`):

| Provider | Content-Type | Key fields |
|---|---|---|
| `cloudmailin` | JSON | `envelope.to[0]`, `headers.Subject`, `plain`, `headers.In-Reply-To` |
| `mailgun` | form-data | `recipient`, `subject`, `stripped-text`, `In-Reply-To` |
| `postmark` | JSON | `To`, `Subject`, `StrippedTextReply`, `Headers[In-Reply-To]` |
| `generic` | JSON | `to`, `subject`, `body`, `in_reply_to` |

All adapters normalise to:
```python
{to: str, subject: str, body: str, in_reply_to: str | None}
```

Logic:
1. Normalise payload via adapter
2. `re.search(r'folder-([0-9a-f-]{36})', to)` → `folder_id`
3. Return 400 if no UUID found
4. `get_item(db, folder_id, user_id)` — reuses `document_service.get_item`
5. Return 404 if folder not found
6. Skip (return 200) if `in_reply_to` is set
7. `prompt = f"{subject}\n\n{body}"`
8. `content = await generation_service.generate_text(prompt, settings)`
9. Upload to MinIO + create document + publish Kafka event
10. Return `{"document_id": str, "status": "processing"}`

**Auth**: no JWT required (called by email provider). Optionally verify `X-Webhook-Signature` HMAC when `settings.webhook_secret` is set.

---

## Files to Modify

### 3. `backend/api_gateway/config.py`
Add `webhook_email_domain`, `webhook_secret`, `email_provider` settings (above).

### 4. `backend/api_gateway/main.py`
```python
from routers import webhooks
app.include_router(webhooks.router, prefix="/api")
```

### 5. `backend/api_gateway/routers/folders.py`
New endpoint:
```
GET /api/folders/{folder_id}/email
```
Returns `{"email": "folder-{uuid}@{domain}"}`.  
In dev, also returns the Cloudmailin variant if `webhook_email_domain == "mail.localhost"` and a `cloudmailin_base` env is set.

### 6. `frontend/src/hooks/useDocuments.ts`
Add `useFolderEmail(folderId: string)` — `useQuery` on `GET /api/folders/{id}/email`.

### 7. `frontend/src/components/documents/detailspane/index.tsx`
In the **folder** Properties section, add:
```
Email Address   folder-{uuid}@domain.com  [copy]
```
- Rendered only when `!isDoc`
- `ButtonEmpty` with clipboard copy icon (`Copy` from `@planview/pv-icons`)
- Data from `useFolderEmail(item.id)`

---

## Dev Testing (step-by-step)

```bash
# 1. Start ngrok
ngrok http 8081

# 2. Set Cloudmailin webhook URL → https://<ngrok-id>.ngrok.io/api/webhooks/email
#    Set format: JSON (CloudMailin Standard)

# 3. Add to .env
WEBHOOK_EMAIL_DOMAIN=cloudmailin.net
EMAIL_PROVIDER=cloudmailin

# 4. Get a folder UUID from the UI or API
FOLDER_ID=<uuid>

# 5. Send a test email to:
#    abc123+folder-{FOLDER_ID}@cloudmailin.net
#
# Or simulate via curl (bypasses Cloudmailin):
curl -X POST http://localhost:8081/api/webhooks/email \
  -H "Content-Type: application/json" \
  -d '{
    "envelope": {"to": ["abc123+folder-'$FOLDER_ID'@cloudmailin.net"], "from": "you@example.com"},
    "headers": {"Subject": "Q3 Security Policy"},
    "plain": "Write a comprehensive Q3 security policy covering access control, data classification, and incident response.",
    "reply_plain": null
  }'
```

---

## Verification
1. POST the curl above with a real folder UUID
2. Confirm 200 response with `document_id`
3. `GET /api/documents?parent_id={folder_id}` → new document appears with status PROCESSING
4. Wait for pipeline → status becomes COMPLETED with generated content as summary
5. UI: open folder details pane → email address row visible with copy button
