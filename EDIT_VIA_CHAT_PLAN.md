# Plan: Document Edit via Chat

## Context
Users want to request natural-language document modifications from the chat window. The system should propose a diff preview, require explicit approval before persisting, and maintain a version history. The document's **extracted text** (stored in MinIO `processed` bucket at `{doc_id}/text.txt`) is the edit target — it drives all downstream processing (chunking → embedding → summarization). Approving an edit re-triggers the pipeline from the CHUNKING stage.

---

## Implementation Order

### 1. Alembic migration — `006_document_edits.py`
New file: `backend/api_gateway/alembic/versions/006_document_edits.py`
```sql
CREATE TABLE document_edits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  user_id     UUID NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
  instruction      TEXT        NOT NULL,
  original_content TEXT        NOT NULL,
  proposed_content TEXT        NOT NULL,
  status           VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_document_edits_document_id ON document_edits (document_id);
```
Pattern: copy raw-SQL `op.execute()` style from `004_compliance_tables.py`. revision=`"006"`, down_revision=`"005"`.

---

### 2. SQLAlchemy model — `models/edit.py`
New file following `models/compliance.py` pattern. Add relationship to `Document`:
```python
# models/document.py — append inside Document class
edits: Mapped[list["DocumentEdit"]] = relationship(
    "DocumentEdit", cascade="all, delete-orphan",
    order_by="DocumentEdit.created_at.desc()"
)
```

---

### 3. Pydantic schemas — `schemas/edit.py`
New file. Key types:
- `EditCreateRequest(instruction: str)`
- `DocumentEditResponse(id, document_id, instruction, original_content, proposed_content, status, created_at)`
- `EditListResponse(edits: list[DocumentEditResponse])`

---

### 4. Kafka schemas — `schemas/kafka_events.py`
Add `TextExtractedEvent` (mirrors `workers/shared/schemas.py`) so the API gateway can publish to the `text_extracted` topic to restart the pipeline from CHUNKING.
Add `TEXT_EXTRACTED = "text_extracted"` to `Topics`.

---

### 5. RAG service `/edit` endpoint
New file: `backend/rag_service/routers/edit.py`

```
POST /edit
body:    { document_text: str, instruction: str }
returns: { proposed_text: str }
```

Uses existing `llm_client.generate(prompt)` (non-streaming). New prompt template in `utils/prompt_templates.py`:
> "Apply ONLY the requested change. Preserve all formatting, structure, headings. Return only the full modified document text. If the change cannot be applied, return the document unchanged."

Register in `backend/rag_service/main.py` alongside `query.router`.

---

### 6. Backend service — `services/document_edit_service.py`
New file. Key functions:

**`create_edit_draft(doc_id, user_id, instruction, db)`**
1. Verify document ownership via `get_item()`
2. Read extracted text from MinIO: `storage_service.download_file(minio_bucket_processed, f"{doc_id}/text.txt")`
3. POST to `{rag_service_url}/edit` via `httpx.AsyncClient(timeout=300)`
4. Save `DocumentEdit(status="pending")` → return response

**`approve_edit(edit_id, user_id, db)`**
1. Guard: `status != "pending"` → raise
2. Write `proposed_content` back to MinIO at same key
3. Reset processing jobs (CHUNKING, EMBEDDING, SUMMARIZATION) → `PENDING`
4. Delete stale `document_embeddings`, `document_chunks`, `document_summaries`
5. Set `documents.status = 'PROCESSING'`
6. Set `edit.status = "approved"` → commit
7. Publish `TextExtractedEvent` to `text_extracted` Kafka topic

**`reject_edit(edit_id, user_id, db)`** — set status=rejected, commit.

**`list_edits(doc_id, user_id, db)`** — query ordered by `created_at DESC`.

---

### 7. API Gateway router — `routers/edits.py`
New file, pattern from `routers/compliance.py`:
```
POST   /api/documents/{id}/edits                  → create_edit_draft (201)
GET    /api/documents/{id}/edits                  → list_edits
POST   /api/documents/{id}/edits/{eid}/approve    → approve_edit
POST   /api/documents/{id}/edits/{eid}/reject     → reject_edit
```
Register in `backend/api_gateway/main.py`.

---

### 8. Frontend types — `src/types/index.ts`
- Add `"edit_proposal"` to `ChatMessage.role` union
- Add optional `editProposal?: { edit_id, document_id, original_content, proposed_content, status }` field to `ChatMessage`

---

### 9. Frontend API — `src/api/edits.ts`
New file, pattern from `src/api/compliance.ts`. Exports `editsApi` with `propose`, `list`, `approve`, `reject`.

---

### 10. EditProposalCard component — `src/components/chat/EditProposalCard.tsx`
Shows a scrollable diff view (added lines green / removed lines red, using `color.success0/100` and `color.error0/100` — same tokens as `ComplianceTab.tsx` RuleRow) and two action buttons (Approve / Reject) using `ButtonEmpty` + `CheckmarkCircleFilled` / `CrossCircleFilled` icons.

**Diff algorithm:** inline Myers line-diff (no new npm package). Context window: ±5 unchanged lines, collapse remainder with "Show N unchanged lines".

`EditProposalCard` manages its own `localStatus` state — updates to `"approved"` / `"rejected"` on mutation success to hide buttons after the decision. Invalidates `["document", documentId]` React Query key on approve so the DetailsPane status refreshes.

---

### 11. ChatWindow.tsx — `src/components/chat/ChatWindow.tsx`
Add edit-intent detection before the existing `streamChat` path:
```typescript
const EDIT_INTENT_RE = /\b(update|add|remove|rewrite|change|modify|edit|fix|delete|replace|insert|correct)\b/i;
```
When matched (and `documentId` is present): call `editsApi.propose()` instead of `streamChat()`, push an `"edit_proposal"` message with a loading status, then populate `editProposal` on completion.

---

### 12. Message.tsx — `src/components/chat/Message.tsx`
Add a new branch: when `msg.role === "edit_proposal"`, render `<EditProposalCard>` (with loading `<StatusText>` while `editProposal` is not yet populated).

---

### 13. Version history tab — DetailsPane
**New:** `src/components/documents/detailspane/EditHistoryList.tsx`
Timeline list using `editsApi.list()` via `useQuery`. Each row: instruction text, status Chip, timestamp. Pattern from `ComplianceTab.tsx`.

**New hook:** `src/hooks/useEdits.ts` — `useDocumentEdits(documentId)` wrapping `editsApi.list`.

**Modified:** `src/components/documents/detailspane/index.tsx`
- Add `"history"` to `DetailTab` type
- Add History tab (shown when `canChat`)
- Render `<EditHistoryList documentId={doc.id} />` when active

---

## Key Files

| File | Change |
|------|--------|
| `backend/api_gateway/alembic/versions/006_document_edits.py` | New migration |
| `backend/api_gateway/models/edit.py` | New model |
| `backend/api_gateway/models/document.py` | Add `edits` relationship |
| `backend/api_gateway/schemas/edit.py` | New schemas |
| `backend/api_gateway/schemas/kafka_events.py` | Add `TextExtractedEvent` |
| `backend/api_gateway/services/document_edit_service.py` | New service |
| `backend/api_gateway/routers/edits.py` | New router |
| `backend/api_gateway/main.py` | Register edits router |
| `backend/rag_service/routers/edit.py` | New `/edit` endpoint |
| `backend/rag_service/utils/prompt_templates.py` | Add `EDIT_PROMPT` |
| `backend/rag_service/main.py` | Register edit router |
| `frontend/src/types/index.ts` | Extend `ChatMessage` |
| `frontend/src/api/edits.ts` | New API module |
| `frontend/src/components/chat/EditProposalCard.tsx` | New component |
| `frontend/src/components/chat/ChatWindow.tsx` | Edit intent detection |
| `frontend/src/components/chat/Message.tsx` | Render edit proposal |
| `frontend/src/components/documents/detailspane/EditHistoryList.tsx` | New component |
| `frontend/src/components/documents/detailspane/index.tsx` | History tab |
| `frontend/src/hooks/useEdits.ts` | New hook |

---

## Verification
1. `make migrate` — migration applies cleanly
2. `make down && make build && make up` — all services healthy
3. Upload a document, wait for COMPLETED
4. In chat: type "update the introduction to be more concise"
5. `EditProposalCard` appears with diff view and Approve / Reject buttons
6. Approve → document re-enters PROCESSING → pipeline completes → new summary
7. History tab → approved edit visible in timeline
8. Reject a proposal → card shows rejected state, pipeline not triggered
