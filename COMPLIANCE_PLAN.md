# Plan: AI-Powered Document Compliance & Governance

> **Status:** Implemented ✓
> Last updated: 2026-06-04

---

## Context

The document intelligence platform currently handles upload → extraction → chunking → embedding → summarization, but has no concept of compliance. This plan adds a full compliance layer: compliance managers define rules, every document is automatically checked after summarization completes, the compliance worker then generates LLM-powered insights explaining what failed and how to fix it, document owners see color-coded compliance badges and a per-rule breakdown tab with actionable insights, and admins get a dashboard showing org-wide compliance health. Compliance is advisory — it never blocks document access or chat.

---

## Architecture Summary

- **New Kafka consumer group** (`compliance-workers`) listens on the existing `summary_generated` topic — no new topic needed.
- **Three new DB tables**: `compliance_rules`, `compliance_reports`, `compliance_rule_results`.
- **New worker service** (`worker_compliance`) runs the four rule types, writes results, then calls the LLM to generate per-document compliance insights stored in `compliance_reports.insights`.
- **New API router** (`/api/compliance/...`) exposes rules CRUD, per-document reports (including insights), re-scan, and dashboard aggregations.
- **New frontend page** (`/compliance`) with stats cards + issues list + rules management.
- **New details pane tab** ("Compliance") shown for completed documents — includes rule breakdown and a highlighted "Insights & Recommendations" section.
- **Compliance badge column** added to the document list (via `compliance_status` field embedded in the list API response).

---

## Phase 1: Database

### Three new models — `backend/api_gateway/models/compliance.py`

```
compliance_rules
  id UUID PK
  name VARCHAR(255) NOT NULL
  description TEXT
  rule_type VARCHAR(50) NOT NULL   -- keyword_required|keyword_forbidden|age_limit_days|llm_check
  params JSONB NOT NULL            -- {"keywords":[...]} or {"days":365} or {"policy":"..."}
  severity VARCHAR(20) NOT NULL    -- critical|warning
  is_active BOOLEAN NOT NULL DEFAULT true
  created_at TIMESTAMPTZ DEFAULT now()
  updated_at TIMESTAMPTZ DEFAULT now()

compliance_reports
  id UUID PK
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE
  status VARCHAR(20) NOT NULL      -- COMPLIANT|WARNING|NON_COMPLIANT|UNCHECKED
  checked_at TIMESTAMPTZ DEFAULT now()
  rules_hash VARCHAR(64) NOT NULL  -- SHA-256 of active rule ids+updated_at; stale detection
  is_current BOOLEAN NOT NULL DEFAULT true
  insights TEXT                    -- LLM-generated plain-English explanation + recommendations
  created_at TIMESTAMPTZ DEFAULT now()

compliance_rule_results
  id UUID PK
  report_id UUID NOT NULL REFERENCES compliance_reports(id) ON DELETE CASCADE
  rule_id UUID REFERENCES compliance_rules(id) ON DELETE SET NULL
  rule_name VARCHAR(255) NOT NULL  -- snapshotted at check time
  rule_type VARCHAR(50) NOT NULL
  severity VARCHAR(20) NOT NULL
  passed BOOLEAN NOT NULL
  detail TEXT                      -- "keyword 'ssn' found" or LLM reason
  locations JSONB                  -- WHERE in the document (see structure below)
  created_at TIMESTAMPTZ DEFAULT now()

-- locations JSONB structure (null for age_limit_days):
-- [{"chunk_index": 3, "page_number": 2, "excerpt": "...your SSN is required for..."}]
-- keyword rules: one entry per matching chunk
-- llm_check: [{"chunk_index": null, "page_number": null, "excerpt": "<summary quote>"}]
```

### Migration — `backend/api_gateway/alembic/versions/004_compliance_tables.py`

- Raw SQL `op.execute()` style matching `001_initial_schema.py`
- Also adds: `ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT false`
- Indexes: `ix_compliance_rules_is_active`, `ix_compliance_reports_document_id`, `ix_compliance_reports_is_current`, `ix_compliance_reports_status`, `ix_compliance_rule_results_report_id`

### User model update — `backend/api_gateway/models/user.py`

Add `is_admin: Mapped[bool]` — used for admin-only rule mutations.

---

## Phase 2: Compliance Worker

### File structure

```
backend/workers/compliance/
  __init__.py
  consumer.py          ← ComplianceConsumer(BaseConsumer) — same pattern as summarization
  engine.py            ← run_compliance_check(document_id, session)
  rules/
    __init__.py
    base.py            ← abstract RuleChecker + RuleResult dataclass
    keyword_required.py
    keyword_forbidden.py
    age_limit_days.py
    llm_check.py       ← uses shared/providers llm_factory.generate()
```

### `consumer.py`

Consumes `summary_generated` with consumer group `compliance-workers`. Calls `run_compliance_check(document_id)` per message.

### `engine.py` — steps

1. Load all active rules from `compliance_rules`
2. Compute `rules_hash` = SHA-256 of sorted `"{id}:{updated_at}"` strings
3. Fetch chunks with `chunk_index` + `page_number` from `document_chunks`
4. Fetch active summary from `document_summaries WHERE is_active=true`
5. Fetch `created_at` and `name` from `documents`
6. For each rule → `RuleChecker.check(params, chunks_with_meta, summary, created_at)` → `RuleResult(passed, detail, locations)`
7. Aggregate: any critical failure → `NON_COMPLIANT`; any warning failure → `WARNING`; else `COMPLIANT`
8. **Generate LLM insights** (only if not `COMPLIANT`): list failed rules + detail in prompt → plain-English explanation + remediation steps → stored in `insights`; fail-open if LLM unavailable
9. Mark old reports `is_current=false`
10. Insert new `ComplianceReport` + one `ComplianceRuleResult` per rule

### Rule types

| Rule | Logic | Locations |
|---|---|---|
| `keyword_required` | scan chunks case-insensitively; ≥1 must contain any keyword | first matching chunk; `[]` if absent |
| `keyword_forbidden` | scan chunks; any match → fail | all matching chunks with 80-char excerpt centred on keyword |
| `age_limit_days` | `(now - created_at).days > days` | `null` (document-level) |
| `llm_check` | LLM evaluates summary vs policy; returns `{"compliant", "reason", "relevant_excerpt"}` | `[{chunk_index: null, page_number: null, excerpt: relevant_excerpt}]` |

**Excerpt generation:** 40 chars before + keyword + 40 chars after, newlines replaced with spaces.

### LLM prompts

**`llm_check` rule:**
```
/no_think
Evaluate whether this document summary complies with the policy.
Policy: {policy}
Summary: {summary}
Respond ONLY with JSON: {"compliant": true, "reason": "...", "relevant_excerpt": "... (max 120 chars)"}
```

**Insights generation (engine.py, non-COMPLIANT only):**
```
/no_think
Document "{doc_name}" failed these compliance checks:
- [CRITICAL] {rule_name}: {detail}
- [WARNING] {rule_name}: {detail}
...
Provide: 1) plain-English explanation of why each check failed. 2) Concrete remediation steps.
Be concise (3-6 sentences). Document summary: {summary}
```

---

## Phase 3: API Gateway

### New files

- `backend/api_gateway/models/compliance.py`
- `backend/api_gateway/schemas/compliance.py`
- `backend/api_gateway/services/compliance_service.py`
- `backend/api_gateway/routers/compliance.py`

### Endpoints — prefix `/api/compliance`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/rules` | any user | List all rules |
| POST | `/rules` | admin | Create rule |
| PATCH | `/rules/{rule_id}` | admin | Update rule |
| DELETE | `/rules/{rule_id}` | admin | Delete rule |
| GET | `/documents/{document_id}` | any user | Report + per-rule results + `is_stale` + `insights` |
| POST | `/documents/{document_id}/scan` | any user | Trigger re-scan (202, BackgroundTasks) |
| GET | `/stats` | any user | `{compliant, warning, non_compliant, unchecked, total_documents}` |
| GET | `/issues` | any user | Paginated issues, params: `cursor`, `limit`, `status_filter` |

**New dependency in `backend/api_gateway/dependencies.py`:**
```python
async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

**Stale detection:** recompute rules hash at read time; if differs from stored hash → `is_stale=True` in response.

**Document list embedding:** LEFT JOIN `compliance_reports (is_current=true)` in the list query to add `compliance_status` to each item — avoids N+1 requests.

---

## Phase 4: Seeding — 15 industry-standard rules

`backend/api_gateway/seed.py` — `seed_compliance_rules(db)` (idempotent):

**PII & Sensitive Data — critical**
| Rule | Type | Keywords |
|---|---|---|
| No PII — SSN | keyword_forbidden | `["social security number", "ssn"]` |
| No PII — Credit Card | keyword_forbidden | `["credit card number", "card number", "cvv", "cvc"]` |
| No PII — Passport / Driver License | keyword_forbidden | `["passport number", "driver license number"]` |
| No Passwords or Secrets | keyword_forbidden | `["password:", "api_key", "secret_key", "private_key", "access_token"]` |
| No Bank Account Details | keyword_forbidden | `["bank account number", "routing number", "iban", "swift code"]` |

**Legal & Document Hygiene — warning**
| Rule | Type | Params |
|---|---|---|
| Required Legal Disclaimer | keyword_required | `["disclaimer", "not legal advice", "for informational purposes"]` |
| Required Confidentiality Notice | keyword_required | `["confidential", "proprietary", "confidentiality"]` |
| Required Copyright Notice | keyword_required | `["©", "copyright", "all rights reserved"]` |
| Document Review Freshness | age_limit_days | `{"days": 365}` |
| Document Staleness Warning | age_limit_days | `{"days": 730}` — critical |

**Content Quality — LLM checks**
| Rule | Severity | Policy |
|---|---|---|
| No Offensive Language | critical | Must not contain offensive/discriminatory language |
| GDPR Compliance Language | warning | Must reference GDPR if handling personal data |
| No Misleading Claims | warning | Must not contain unsubstantiated claims |
| Regulatory Framework Reference | warning | Should reference applicable regulatory standards |
| Professional Tone and Quality | warning | Must be professional, coherent, not placeholder text |

Also: set seeded admin user `is_admin=True`.

---

## Phase 5: Docker & Config

- **`backend/workers/config.py`**: add `kafka_consumer_group_compliance: str = "compliance-workers"`
- **`backend/workers/worker_runner.py`**: add `"compliance": "compliance.consumer.ComplianceConsumer"` to `WORKER_MAP`
- **`docker-compose.yml`**: add `worker_compliance` service (1 replica, `WORKER_TYPE: compliance`, same pattern as `worker_summarization`)

---

## Phase 6: Frontend

### New files

```
frontend/src/
  types/compliance.ts           ← ComplianceStatus | RuleType | Severity | ComplianceRule
                                   ComplianceReport (status, insights, is_stale, results)
                                   ComplianceRuleResult (passed, detail, locations: Location[])
                                   Location = {chunk_index, page_number, excerpt}
                                   ComplianceStats | ComplianceIssueItem | ComplianceIssuesResponse
  api/compliance.ts             ← getRules, createRule, updateRule, deleteRule,
                                   getReport, triggerScan, getStats, getIssues
  hooks/useCompliance.ts        ← useComplianceRules, useComplianceReport, useTriggerScan,
                                   useComplianceStats, useComplianceIssues,
                                   useCreateRule, useUpdateRule, useDeleteRule
  pages/Compliance.tsx          ← Full page: Dashboard tab + Rules tab
  components/compliance/
    ComplianceBadge.tsx         ← COMPLIANT=green | WARNING=amber | NON_COMPLIANT=red | UNCHECKED=gray
    ComplianceTab.tsx           ← Overall badge → stale warning → Insights panel → rule list
                                   with location chips → Re-scan button with spinner
    DashboardStats.tsx          ← 4 clickable stat cards
    IssuesList.tsx              ← Paginated issues grid (@planview/pv-grid)
    RulesManagement.tsx         ← Rules list; edit/delete only shown to admins
    RuleFormDialog.tsx          ← Create/edit modal; dynamic params by rule_type
```

### Modified files

| File | Change |
|---|---|
| `frontend/src/App.tsx` | Add `/compliance` route |
| `frontend/src/components/layout/AppNavigationBar.tsx` | Add Compliance nav link |
| `frontend/src/components/documents/detailspane/index.tsx` | Add `"compliance"` to `DetailTab`; add Compliance tab for COMPLETED docs |
| `frontend/src/components/documents/ItemList.tsx` | Add `compliance` column with `ComplianceBadge` |
| `frontend/src/types/index.ts` | Add `compliance_status: ComplianceStatus \| null` to `Item` |

### `ComplianceTab.tsx` — per-rule display

Each failed rule shows:
- Rule name + severity chip + pass/fail icon
- `detail` text (e.g. "Keyword 'ssn' found in 2 locations")
- Location chips: `Page 3 · Chunk 7` — expand to show `excerpt` with keyword bolded
- LLM rules: `relevant_excerpt` shown as italic blockquote
- Age limit: no chips (document-level only)

Plus:
- **Stale banner** (amber): "Rules updated since last scan — results may be outdated"
- **Insights panel**: bordered card with "Recommendations" heading — plain text, visible only when `insights` non-null
- **Re-scan button**: "Scanning…" spinner during pending; auto-refetches on success

### Admin detection

Decode `is_admin` from JWT payload (UI-only, no-verify) and store in `authStore`. Used to show/hide admin controls. Server enforces 403 regardless.

---

## Implementation Order

1. DB model + migration 004
2. Update `alembic/env.py` + `models/__init__.py`
3. `is_admin` on User model + seed update
4. Compliance worker: rules → engine → consumer → runner + config
5. API: schemas → service → router → `main.py`
6. Seed 15 default rules
7. Document list LEFT JOIN for `compliance_status`
8. Docker `worker_compliance` service
9. Frontend: types → API → hooks → badge → ComplianceTab → details pane → dashboard page → routing + nav

---

## Verification Checklist

- [ ] `alembic upgrade 004` + `alembic downgrade 003` — tables created and dropped cleanly
- [ ] `GET /api/compliance/rules` returns 15 rules after fresh seed
- [ ] Upload PDF → `COMPLETED` → `GET /api/compliance/documents/{id}` shows report with `locations` on each keyword result
- [ ] Document with forbidden keyword: `locations[0].excerpt` contains the keyword, `page_number` is accurate
- [ ] Document list shows compliance badge column with correct color
- [ ] Details pane Compliance tab: Insights panel visible if non-COMPLIANT, location chips clickable
- [ ] Re-scan: spinner → `checked_at` updates → results refresh
- [ ] `/compliance` dashboard: stat cards + issues list load correctly
- [ ] Stale detection: edit a rule → `is_stale: true` in report → frontend banner appears
- [ ] Non-admin `POST /api/compliance/rules` → 403

## Implementation Log

| Phase | Files Created/Modified | Status |
|---|---|---|
| DB models | `models/compliance.py`, `004_compliance_tables.py`, `models/user.py`, `models/document.py`, `models/__init__.py`, `alembic/env.py` | ✓ |
| Compliance worker | `workers/compliance/` (consumer, engine, 4 rule checkers) | ✓ |
| API gateway | `schemas/compliance.py`, `services/compliance_service.py`, `routers/compliance.py`, `main.py`, `seed_compliance.py`, `auth_service.py`, `routers/auth.py` | ✓ |
| Seeding | 15 industry-standard rules seeded on startup | ✓ |
| Docker | `worker_compliance` service added to `docker-compose.yml`, `workers/config.py`, `worker_runner.py` | ✓ |
| Frontend data | `types/compliance.ts`, `api/compliance.ts`, `hooks/useCompliance.ts`, `types/index.ts` | ✓ |
| Frontend UI | `ComplianceBadge`, `ComplianceTab`, `DashboardStats`, `IssuesList`, `RulesManagement`, `RuleFormDialog` | ✓ |
| Frontend wiring | `App.tsx`, `AppNavigationBar.tsx`, `detailspane/index.tsx`, `ItemList.tsx`, `authStore.ts` | ✓ |
| Backend list | `document_service.py` batch compliance status lookup, `schemas/document.py` `compliance_status` field | ✓ |
