"""
Scenario B — Feature: "AI-Powered Smart Ticket Routing"

A new ML feature that automatically assigns incoming support tickets to the
most relevant agent based on ticket content, customer tier, and agent
specialization. Meridian HR (mid-market customer) requested it.

Cross-links:
  Confluence Design Doc      ← Jira FRG-2001 references it; Slack thread references it
  Confluence Rollout Runbook ← Jira FRG-2001/2002; Slack thread
  Jira FRG-2001 (Epic)       ← parent of FRG-2002; references Confluence design doc
  Jira FRG-2002 (Story)      ← classifier API; references GitHub PR #89
  Slack #product-eng         ← design review; references FRG-2001, PR #89
  GitHub PR #89              ← fixes FRG-2002; links FRG-2001
  HubSpot Meridian HR        ← feature requestor; in evaluation stage
"""

DOCUMENTS = [

    # ── Confluence: Design Doc ─────────────────────────────────────────────────
    {
        "source_type": "confluence",
        "filename": "[seed] confluence-design-doc-smart-ticket-routing-v1.txt",
        "data": {
            "title": "Design Doc: Smart Ticket Routing v1",
            "space": "product-eng",
            "author": "priya.nair@forge.io",
            "status": "published",
            "confidentiality": "internal",
            "labels": "design-doc, AI, support, ticket-routing",
            "content": """## Status: APPROVED — 2026-04-10

**Author:** Priya Nair (Product Engineering)
**Reviewers:** Rahul Sharma, Dev Patel, Sofia Chen (CS)
**Jira Epic:** FRG-2001

---

## Problem

Forge's support team currently assigns incoming tickets manually. With 400+ tickets/day, this creates:
- Average 18-minute assignment delay (P1 SLA requires <5 min)
- Agent expertise mismatch: billing questions routed to infra engineers, etc.
- Bottleneck when team lead is unavailable

Customers (notably Meridian HR, see HubSpot) have specifically requested auto-routing as a prerequisite for upgrading to the enterprise tier.

---

## Proposed Solution

Train a lightweight text classifier on Forge's historical ticket data to predict the correct support queue (billing, infra, integrations, onboarding, bug-report). Route new tickets automatically; human override always available.

---

## Architecture

```
Incoming ticket (webhook)
    ↓
Ticket Routing Service (new microservice)
    ├── Preprocessing: extract subject + body + customer tier
    ├── Classifier: scikit-learn LinearSVC (TF-IDF features)
    │   → predicts queue: billing | infra | integrations | onboarding | bug-report
    ├── Confidence threshold: if confidence < 0.65 → manual review queue
    └── Assignment: PATCH /api/tickets/{id}/assignee via Forge internal API
```

**Model choice:** LinearSVC over BERT. Rationale:
- Ticket text is short (<500 tokens avg)
- Latency requirement: <200ms p99 (LinearSVC: ~5ms, BERT: ~180ms)
- Interpretability: feature weights useful for debugging misroutes
- Training data: 22,000 historical tickets (4 months); retrain weekly

---

## API Contract

### POST /internal/routing/classify

Request:
```json
{
  "ticket_id": "uuid",
  "subject": "string",
  "body": "string",
  "customer_tier": "starter | mid-market | enterprise",
  "created_at": "iso8601"
}
```

Response:
```json
{
  "predicted_queue": "billing | infra | integrations | onboarding | bug-report | manual-review",
  "confidence": 0.87,
  "model_version": "v1.2.0",
  "features": ["billing", "invoice", "payment"]
}
```

---

## Rollout Plan

1. **Week 1** (shadow mode): Classifier runs on all tickets but does NOT assign — results logged only. Compare with human decisions.
2. **Week 2** (starter tier only): Auto-assign for starter accounts; enterprise/mid-market still manual.
3. **Week 3** (all tiers): Full rollout if shadow mode accuracy >90%.

Feature flag: `smart_routing_enabled` (per-account and global). Runbook: see "Runbook: Smart Routing Feature Flag Rollout".

---

## Accuracy Targets

| Metric | Target |
|--------|--------|
| Overall accuracy | >90% |
| P1 ticket accuracy | >97% |
| False positive (enterprise wrong-queue) | <2% |
| p99 latency | <200ms |

---

## Open Questions (resolved)

- **Q: What if a ticket spans multiple queues?** → Route to primary queue; add secondary label for agent awareness. Implemented.
- **Q: How do we handle new ticket types we haven't seen?** → Confidence <0.65 → manual-review queue. Implemented.
- **Q: GDPR / data minimization?** → Classifier runs on-prem (no third-party ML API). Ticket content not stored by classifier. Legal approved 2026-04-08.
""",
        },
    },

    # ── Confluence: Rollout Runbook ────────────────────────────────────────────
    {
        "source_type": "confluence",
        "filename": "[seed] confluence-runbook-smart-routing-feature-flag-rollout.txt",
        "data": {
            "title": "Runbook: Smart Routing Feature Flag Rollout",
            "space": "product-eng",
            "author": "dev.patel@forge.io",
            "status": "published",
            "confidentiality": "internal",
            "labels": "runbook, smart-routing, feature-flag, rollout",
            "content": """## Purpose

Step-by-step guide for rolling out the smart ticket routing feature (FRG-2001/FRG-2002). Three-phase rollout using the `smart_routing_enabled` feature flag.

---

## Prerequisites

- PR #89 (forge-app/support-service) merged and deployed to production
- Classifier model `v1.2.0` loaded in `forge-routing-service`
- Shadow mode accuracy report reviewed (must show >90% accuracy on last 7 days)
- On-call engineer aware of rollout

---

## Phase 1 — Shadow Mode (Week 1)

**What it does:** Classifier runs on all new tickets, logs predictions, but does NOT auto-assign. Zero customer impact.

```bash
# Enable shadow mode globally
forge-flags set smart_routing_enabled=shadow --env prod

# Verify flag is active
forge-flags get smart_routing_enabled --env prod
# Expected: { "value": "shadow", "scope": "global" }

# Monitor shadow mode dashboard
# Grafana → Support → Smart Routing → Shadow Mode Accuracy
```

**Go / No-go criteria after 7 days:**
- Overall accuracy ≥90% on last 7 days of tickets
- P1 ticket accuracy ≥97%
- No customer-visible errors in routing service logs

---

## Phase 2 — Starter Tier Only (Week 2)

**What it does:** Auto-assign tickets for `starter` tier accounts. Enterprise and mid-market remain manual.

```bash
# Enable for starter tier only
forge-flags set smart_routing_enabled=active --tier starter --env prod

# Verify
forge-flags get smart_routing_enabled --env prod
# Expected: { "value": "active", "scope": "tier:starter" }
```

**Rollback if issues:**
```bash
forge-flags set smart_routing_enabled=shadow --env prod
```

**Monitoring:** Watch `#support-ops` Slack channel for mis-routing complaints.

---

## Phase 3 — All Tiers (Week 3)

```bash
# Full rollout
forge-flags set smart_routing_enabled=active --env prod

# Verify per-account override still works
forge-flags set smart_routing_enabled=disabled --account <account_id> --env prod
```

**Rollback procedure:**
```bash
# Immediate full rollback
forge-flags set smart_routing_enabled=disabled --env prod

# Optionally re-run manual assignment for last 2h of misrouted tickets:
SELECT * FROM support_tickets WHERE assigned_by='smart_router' AND created_at > now() - interval '2 hours';
```

---

## Escalation

If accuracy drops below threshold or customer complaints spike:
1. Post in `#product-eng` with metrics
2. Roll back to shadow mode
3. Create Jira ticket under FRG epic with classifier failure details
4. Page Priya Nair (ML feature owner) via PagerDuty routing: `forge-ml-oncall`
""",
        },
    },

    # ── Jira: FRG-2001 (Epic) ─────────────────────────────────────────────────
    {
        "source_type": "jira",
        "filename": "[seed] jira-FRG-2001-smart-ticket-routing-epic.txt",
        "data": {
            "key": "FRG-2001",
            "project": "forge",
            "issue_type": "Epic",
            "summary": "Smart ticket routing (AI-powered auto-assignment)",
            "status": "In Progress",
            "priority": "P2",
            "reporter": "priya.nair@forge.io",
            "labels": "AI, support, smart-routing, Q2-2026",
            "description": """**Epic for the smart ticket routing feature.**

Automatically assign incoming support tickets to the correct queue using an ML classifier.

**Design doc:** Confluence: "Design Doc: Smart Ticket Routing v1"
**Rollout runbook:** Confluence: "Runbook: Smart Routing Feature Flag Rollout"

**Business case:**
- Reduce ticket assignment delay from 18 min → <2 min
- Eliminate manual routing bottleneck
- Prerequisite for Meridian HR's enterprise upgrade (see HubSpot)

**Child issues:**
- FRG-2002: ML classifier API endpoint + routing engine
- FRG-2003: Shadow mode accuracy dashboard (Grafana)
- FRG-2004: Per-account feature flag override UI

**Acceptance criteria:**
- Shadow mode accuracy >90% on 7-day rolling window
- P1 ticket routing accuracy >97%
- p99 latency <200ms
- Feature flag controls per-account and globally
- Rollout documented in Confluence runbook (above)

**Status:** FRG-2002 merged and in prod. Currently in Phase 2 (starter tier). Phase 3 (all tiers) planned for 2026-06-24.
""",
            "comments": [
                "dev.patel: Phase 1 (shadow mode) complete. 7-day accuracy: 93.2% overall, 98.1% P1. Proceeding to Phase 2.",
                "sofia.chen: Great news! I've shared the accuracy results with Meridian HR. They're excited — this was their top feature request.",
                "priya.nair: Phase 2 started today (starter tier). No issues so far. Monitoring #support-ops for complaints.",
            ],
        },
    },

    # ── Jira: FRG-2002 (Story) ────────────────────────────────────────────────
    {
        "source_type": "jira",
        "filename": "[seed] jira-FRG-2002-classifier-api-endpoint.txt",
        "data": {
            "key": "FRG-2002",
            "project": "forge",
            "issue_type": "Story",
            "summary": "ML classifier API endpoint + routing engine",
            "status": "Resolved",
            "priority": "P2",
            "reporter": "priya.nair@forge.io",
            "labels": "AI, classifier, API, smart-routing",
            "description": """**Part of Epic FRG-2001.**

Implement the ticket routing microservice with the ML classifier and the internal routing API endpoint.

**Requirements:**
- `POST /internal/routing/classify` endpoint (spec in design doc)
- LinearSVC model trained on 22,000 historical tickets
- Feature: TF-IDF on subject + body; customer tier as additional feature
- Confidence threshold: <0.65 → manual-review queue
- Model versioning: store model version in response; retrain pipeline runs weekly
- p99 latency target: <200ms

**PR:** forge-app/support-service#89

**Tests:**
- Unit: classifier accuracy on holdout set (>90%)
- Integration: end-to-end routing for each queue type
- Load: 500 req/s with p99 <200ms (Locust test in PR)
""",
            "comments": [
                "dev.patel: PR #89 up for review. Accuracy on holdout: 93.4%. Latency: p99 = 42ms.",
                "kenji.watanabe: Load test passed: 500 req/s, p99 = 38ms. Well under budget.",
                "priya.nair: Merged. Deployed to prod. Shadow mode starting today.",
            ],
        },
    },

    # ── Slack: #product-eng thread ────────────────────────────────────────────
    {
        "source_type": "slack",
        "filename": "[seed] slack-product-eng-smart-routing-design-review.txt",
        "data": {
            "workspace": "forge-hq",
            "channel": "product-eng",
            "channel_type": "public",
            "title": "Smart ticket routing — design review + rollout discussion",
            "participants": "priya.nair, dev.patel, rahul.sharma, kenji.watanabe, sofia.chen",
            "labels": "AI, smart-routing, design-review",
            "linked_jira_tickets": "FRG-2001, FRG-2002",
            "linked_github_prs": "forge-app/support-service#89",
            "messages": [
                "priya.nair: 👋 Sharing the design doc for smart ticket routing — Confluence: 'Design Doc: Smart Ticket Routing v1'. Please review by EOD Thursday.",
                "dev.patel: Read it. The LinearSVC choice makes sense for latency. One concern: what happens when the model sees a ticket type it was never trained on?",
                "priya.nair: Good question. Anything with confidence <0.65 goes to manual-review queue. Worse than before? No — it's exactly what happens today but with a fallback path explicitly defined.",
                "rahul.sharma: I like the three-phase rollout. Shadow mode first is the right call — we can validate accuracy before any customer sees it.",
                "kenji.watanabe: Who owns the Grafana dashboard for shadow mode accuracy? That's FRG-2003 right?",
                "dev.patel: Yes, I'll take FRG-2003 alongside FRG-2002. The dashboard JSON can live in the same repo.",
                "sofia.chen: Meridian HR is going to love this. Their support ops lead Jenna Park has been asking about auto-routing for 6 months. This is the main thing blocking their enterprise upgrade.",
                "priya.nair: Sofia — noted. I've added a note in the design doc that Meridian HR is a key stakeholder. We should make sure Phase 2 includes mid-market so they can see it before signing.",
                "dev.patel: PR #89 is up — forge-app/support-service#89. Shadow mode deployed. Accuracy so far over 48h: 91.8% overall.",
                "rahul.sharma: 91.8% is well above the 90% bar. Nice work. I'll add this to the weekly eng update.",
                "priya.nair: ✅ Phase 1 complete. 7-day accuracy: 93.2% overall, 98.1% P1. Moving to Phase 2 (starter tier) today. Runbook: Confluence 'Runbook: Smart Routing Feature Flag Rollout'.",
                "sofia.chen: Just told Meridian HR. Jenna was thrilled. Expect an upgrade conversation in the next QBR.",
            ],
        },
    },

    # ── GitHub: PR #89 ────────────────────────────────────────────────────────
    {
        "source_type": "github",
        "filename": "[seed] github-forge-app-support-service-pr-89.txt",
        "data": {
            "repo": "forge-app/support-service",
            "type": "pull_request",
            "number": 89,
            "title": "Smart ticket routing: ML classifier API + shadow mode + DLQ integration",
            "state": "merged",
            "author": "dev.patel",
            "base_branch": "main",
            "labels": "feature, AI, smart-routing, FRG-2001",
            "files_changed": (
                "src/routing/classifier.py, "
                "src/routing/api.py, "
                "src/routing/feature_extractor.py, "
                "src/routing/model/v1.2.0.pkl, "
                "migrations/0051_add_routing_tables.py, "
                "infra/grafana/smart_routing_dashboard.json, "
                "tests/test_classifier.py, "
                "tests/test_routing_api.py, "
                "tests/load/locustfile.py"
            ),
            "linked_issues": "FRG-2002, FRG-2001",
            "body": """## Summary

Implements the smart ticket routing classifier and API endpoint for FRG-2002 (part of epic FRG-2001).

### What's included

**Classifier (`src/routing/classifier.py`):**
- LinearSVC trained on 22,000 historical Forge support tickets
- TF-IDF features on subject + body (max 5,000 features)
- Customer tier encoded as an ordinal feature
- Confidence: decision function score normalized to [0, 1]
- Model version pinned in `config.py`; retrain pipeline in `scripts/retrain.py`

**API (`src/routing/api.py`):**
- `POST /internal/routing/classify` (spec per Confluence design doc)
- Returns: predicted_queue, confidence, model_version, top features
- Latency: p99 = 42ms (Locust load test at 500 req/s)

**Shadow mode:**
- When feature flag `smart_routing_enabled=shadow`, classify and log but do NOT patch ticket assignee
- Logs structured as `routing_shadow_log` table for Grafana dashboard

**Grafana dashboard (`infra/grafana/smart_routing_dashboard.json`):**
- Shadow mode accuracy (7-day rolling window)
- Confidence distribution
- Queue prediction breakdown by tier

### Accuracy results

| Queue | Precision | Recall |
|-------|-----------|--------|
| billing | 95.1% | 93.8% |
| infra | 91.4% | 92.0% |
| integrations | 89.3% | 87.6% |
| onboarding | 94.7% | 96.1% |
| bug-report | 92.8% | 91.4% |
| **Overall** | **93.4%** | **92.6%** |

### Load test

```
500 concurrent users, 60-second ramp
p50:  8ms
p95: 24ms
p99: 42ms
Max: 87ms
Errors: 0
```

### How to deploy

```bash
# Run migration
python manage.py migrate 0051_add_routing_tables

# Load model
cp src/routing/model/v1.2.0.pkl /data/models/

# Restart routing service
kubectl rollout restart deployment/routing-service -n forge-prod

# Enable shadow mode
forge-flags set smart_routing_enabled=shadow --env prod
```
""",
            "comments": [
                "priya.nair: This looks great. Accuracy table is better than our target. One question: are we retraining on new data weekly automatically?",
                "dev.patel: Yes — `scripts/retrain.py` is a cron job (Sunday 02:00 UTC). It retrains on the last 90 days of tickets and only promotes if accuracy > current model. CI runs the holdout test automatically.",
                "kenji.watanabe: Load test numbers are excellent. p99 at 42ms is well under the 200ms SLA. Approved.",
                "rahul.sharma: LGTM. I'd add a note in the runbook about how to trigger an emergency retrain if accuracy degrades. Otherwise excellent.",
                "dev.patel: Good point — added a section to the Confluence rollout runbook. Merging.",
            ],
        },
    },

    # ── HubSpot: Meridian HR ──────────────────────────────────────────────────
    {
        "source_type": "hubspot",
        "filename": "[seed] hubspot-meridian-hr.txt",
        "data": {
            "company_name": "Meridian HR",
            "company_domain": "meridianhr.io",
            "stage": "evaluation",
            "account_tier": "mid-market",
            "industry": "human_resources_software",
            "interested_products": "forge-support, forge-projects, forge-crm",
            "notes": """Meridian HR is an HR software company (250 employees, B2B SaaS). Currently on Forge mid-market plan (~80 seats, $34,000/yr). Has been a customer for 14 months.

Primary contact: Jenna Park, Director of Support Operations (jenna.park@meridianhr.io)

**Upgrade interest:** Jenna has expressed strong interest in upgrading to the enterprise tier ($72,000/yr) but is blocked on one feature: **automated ticket routing**. Her support team handles 120–150 tickets/day; manual assignment creates a 20-minute delay that violates their internal SLA.

**Feature request history:**
- 2025-11-12: Jenna first raised auto-routing in QBR
- 2026-01-09: Formal feature request submitted (FRG-2001 epic)
- 2026-04-10: Design doc approved; roadmap confirmed for Q2 2026
- 2026-06-03: Sofia informed Jenna that Phase 1 (shadow mode) showed 93.2% accuracy. Jenna very positive.
- 2026-06-10: Phase 2 (starter tier) live. Meridian HR is mid-market — Phase 3 (all tiers) needed for them to use it. ETA: 2026-06-24.

**CSM notes (Sofia Chen):** Jenna is reasonable and patient. She understands we're rolling out carefully. As long as Phase 3 ships by end of June, she's committed to the enterprise upgrade. Deal value: +$38,000 ARR.

**Renewal:** Current contract up 2026-09-01. Upgrade likely converts to a new 12-month enterprise contract.
""",
            "next_step": "Notify Jenna when Phase 3 (all tiers) goes live. Schedule enterprise upgrade call for 2026-07-01.",
            "blockers": [
                "Smart routing Phase 3 not yet live (ETA 2026-06-24) — Meridian HR needs all-tiers rollout before they can evaluate",
                "Procurement process at Meridian HR requires 30-day legal review for contracts >$50k — need to start by 2026-08-01 to hit renewal date",
            ],
        },
    },

]
