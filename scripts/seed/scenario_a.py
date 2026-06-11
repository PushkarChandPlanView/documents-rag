"""
Scenario A — P1 Incident: "Notification Delivery Failure"

Forge's own notification service (used to send project deadline reminders,
ticket assignment alerts, and SLA breach notifications to customers) stops
delivering emails. Enterprise customers miss critical SLA deadlines.

Cross-links:
  Confluence SOP          ← Jira FRG-1001 references it
  Confluence Post-Mortem  ← references FRG-1001, FRG-1002, FRG-1003, GitHub PR #55
  Jira FRG-1001           ← linked to Slack #incidents thread
  Jira FRG-1002           ← fix for root cause (queue worker crash)
  Jira FRG-1003           ← follow-up (dead-letter queue)
  Slack #incidents        ← references FRG-1001, GitHub forge-app/notifications-service#55
  GitHub PR #55           ← fixes FRG-1002; linked to FRG-1003
  HubSpot Vertex Analytics← enterprise customer impacted; CSM escalation
"""

DOCUMENTS = [

    # ── Confluence: SOP ────────────────────────────────────────────────────────
    {
        "source_type": "confluence",
        "filename": "[seed] confluence-sop-notification-incident-response.txt",
        "data": {
            "title": "SOP: Notification Service Incident Response",
            "space": "engineering",
            "author": "priya.nair@forge.io",
            "status": "published",
            "confidentiality": "internal",
            "labels": "runbook, notifications, on-call",
            "content": """## Purpose

This runbook defines the response procedure for any incident affecting Forge's notification delivery pipeline (email, in-app alerts, webhook triggers). Follow these steps in order.

---

## Severity Levels

| Severity | Condition | Response SLA |
|----------|-----------|--------------|
| P1 | >10% of notifications failing; enterprise customer impacted | 15 min first response, 4h resolution |
| P2 | Notification delays >5 min; no customer impact confirmed | 30 min first response |
| P3 | Isolated failures, <1% failure rate | Next business day |

---

## Step 1 — Detect

Check the following dashboards:
- **Grafana → Notifications → Queue Depth**: alert fires at >5,000 pending messages
- **PagerDuty → Notification Worker alerts**: fires when worker crash rate >3/hr
- **Elasticsearch logs**: `grep "NotificationWorkerException"` in `forge-notifications-*`

---

## Step 2 — Triage

1. Join `#incidents` on Slack and post the incident commander role
2. Open a Jira incident ticket under project FRG, type = Incident, priority P1 or P2
3. Identify failure mode:
   - **Queue backlog** → worker is alive but slow; check rate-limiting config
   - **Worker crash loop** → check template rendering errors; malformed variables crash the worker (known issue, see FRG-1002)
   - **SMTP relay failure** → check SendGrid status page and API key validity
   - **Database connection exhaustion** → check Postgres connection pool metrics

---

## Step 3 — Mitigate

### Quick mitigation for worker crash loop:
```bash
# Restart notification workers
kubectl rollout restart deployment/notification-worker -n forge-prod

# Check for malformed templates in the queue
SELECT * FROM notification_queue WHERE status='PENDING' AND payload->>'template_vars' IS NULL LIMIT 20;

# Purge malformed messages
UPDATE notification_queue SET status='DEAD_LETTER' WHERE status='PENDING' AND payload->>'template_vars' IS NULL;
```

### If SMTP relay is down:
```bash
# Switch to backup relay (Mailgun)
kubectl set env deployment/notification-worker SMTP_PROVIDER=mailgun -n forge-prod
```

---

## Step 4 — Communicate

- Engineering: post status updates in `#incidents` every 30 min
- Customer Success: notify CSM team via `#cs-escalations`; they will contact affected enterprise accounts
- Status page: update status.forge.io within 15 min of P1 declaration

---

## Step 5 — Resolve & Follow-up

1. Confirm delivery queue is draining (depth < 100 messages)
2. Verify affected customers received all missed notifications (manual backfill if needed)
3. Close the Jira incident ticket and link the post-mortem
4. Post-mortem required for all P1 incidents — use the Post-Mortem Confluence template

---

## Key Contacts

| Role | Person | Slack |
|------|--------|-------|
| On-call engineer | rotation | @oncall-eng |
| Notifications tech lead | Rahul Sharma | @rahul.sharma |
| Customer Success lead | Sofia Chen | @sofia.chen |
| VP Engineering | Marcus Webb | @marcus.webb |
""",
        },
    },

    # ── Confluence: Post-Mortem ────────────────────────────────────────────────
    {
        "source_type": "confluence",
        "filename": "[seed] confluence-post-mortem-frg-1001-notification-outage.txt",
        "data": {
            "title": "Post-Mortem: FRG-1001 Notification Delivery Outage — 2026-05-14",
            "space": "engineering",
            "author": "rahul.sharma@forge.io",
            "status": "published",
            "confidentiality": "internal",
            "labels": "post-mortem, notifications, P1",
            "content": """## Summary

On 2026-05-14 between 14:22 UTC and 18:45 UTC, Forge's notification delivery service experienced a complete outage lasting **4 hours 23 minutes**. Approximately **47,000 notification messages** were undelivered, affecting 3 enterprise customers and 28 mid-market accounts. The root cause was a crash loop in the notification queue worker triggered by a malformed template variable in a bulk notification batch sent by Vertex Analytics.

**Jira incident ticket:** FRG-1001
**Fix:** FRG-1002 (deployed 2026-05-15), FRG-1003 (deployed 2026-05-21)

---

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 14:22 | Vertex Analytics triggers bulk send of 12,400 project deadline reminders via API |
| 14:23 | Notification worker encounters `null` value in `{{project.due_date}}` template variable |
| 14:23 | Worker throws `TemplateRenderException`, crashes, and restarts |
| 14:24 | Worker requeues the same message on restart → immediately crashes again (crash loop) |
| 14:31 | PagerDuty alert fires (worker crash rate >3/hr) |
| 14:35 | On-call engineer Aisha Okonkwo joins `#incidents` |
| 14:42 | Incident declared P1; Rahul Sharma (notifications TL) paged |
| 15:05 | Root cause identified: malformed template variable in Vertex batch |
| 15:18 | Temporary mitigation: malformed messages moved to DEAD_LETTER queue manually |
| 15:22 | Notification queue begins draining |
| 16:00 | All new notifications delivering; backlog of 47,000 messages queued for redelivery |
| 18:45 | Full backlog redelivered; incident resolved |

---

## Root Cause

The notification queue worker did not handle `null` values in template variables. When `{{project.due_date}}` was `null`, the Jinja2 template renderer raised an unhandled `TemplateRenderException`. The worker's retry logic requeued the message without skipping it, causing an infinite crash loop that blocked the entire queue.

**Fix (FRG-1002):** Added null-safe template variable rendering with a fallback placeholder. Deployed in `forge-app/notifications-service` PR #55.

---

## Contributing Factors

1. **No dead-letter queue:** Failed messages blocked the worker instead of being parked. Fixed by FRG-1003 (DLQ implemented in PR #55).
2. **No alerting on queue depth:** The queue depth metric existed but had no alert threshold configured. Added in the same PR.
3. **Bulk API not rate-limited:** Vertex Analytics sent 12,400 messages in a single API call. Rate limiting added as FRG-1004 (follow-up).

---

## Impact

| Segment | Accounts affected | Notifications undelivered |
|---------|------------------|--------------------------|
| Enterprise | 3 (including Vertex Analytics) | ~38,000 |
| Mid-market | 28 | ~9,000 |
| Starter | 0 | 0 |

**Customer: Vertex Analytics** — The triggering account. CSM Sofia Chen spoke to their VP Engineering on 2026-05-14 at 17:00 UTC. Vertex was offered a 15-day service credit. See HubSpot for account notes.

---

## Action Items

| Item | Owner | Jira | Due |
|------|-------|------|-----|
| Null-safe template rendering | Rahul Sharma | FRG-1002 | 2026-05-15 ✅ |
| Dead-letter queue + alerting | Dev Patel | FRG-1003 | 2026-05-21 ✅ |
| Bulk API rate limiting | Kenji Watanabe | FRG-1004 | 2026-06-07 |
| Runbook update (worker crash section) | Aisha Okonkwo | — | 2026-05-28 ✅ |

---

## Lessons Learned

- Crash loops on malformed data are a class of failure we need to handle generically — add a `max_retries=3` poison-pill handler to all queue workers
- Customer-triggered bulk operations should be rate-limited and validated before enqueuing
- The on-call runbook correctly identified the failure mode; response time met P1 SLA
""",
        },
    },

    # ── Jira: FRG-1001 (P1 Incident ticket) ───────────────────────────────────
    {
        "source_type": "jira",
        "filename": "[seed] jira-FRG-1001-notification-delivery-failure.txt",
        "data": {
            "key": "FRG-1001",
            "project": "forge",
            "issue_type": "Incident",
            "summary": "P1: Notification delivery failure — enterprise tier",
            "status": "Resolved",
            "priority": "P1",
            "reporter": "aisha.okonkwo@forge.io",
            "labels": "notifications, incident, enterprise, P1",
            "description": """**Incident declared: 2026-05-14 14:42 UTC**

Notification delivery service is in a crash loop. The queue worker keeps restarting due to an unhandled exception in template rendering. All notifications (email + in-app) are blocked.

**Symptoms:**
- PagerDuty alert: notification worker crash rate >3/hr
- Grafana: queue depth climbing to 47,000+ messages
- Affected: all notification types (deadline reminders, ticket assignments, SLA alerts)

**Customers confirmed affected:**
- Vertex Analytics (enterprise) — triggered the incident with a bulk send
- 2 other enterprise accounts + ~28 mid-market accounts

**Runbook:** See Confluence: "SOP: Notification Service Incident Response"

**Fix tracked in:** FRG-1002 (root cause), FRG-1003 (DLQ follow-up)
**Post-mortem:** See Confluence: "Post-Mortem: FRG-1001 Notification Delivery Outage — 2026-05-14"
""",
            "comments": [
                "aisha.okonkwo: On it. Joined #incidents. Paging Rahul.",
                "rahul.sharma: Root cause found — null template variable in Vertex batch causing crash loop. Moving malformed messages to DEAD_LETTER manually.",
                "aisha.okonkwo: Queue draining. New notifications delivering. Backlog redelivery in progress.",
                "sofia.chen: CSM team notified. Contacted Vertex Analytics VP Eng. Offering 15-day service credit.",
                "rahul.sharma: Incident resolved at 18:45 UTC. All 47k messages redelivered. FRG-1002 fix deploying tomorrow.",
            ],
        },
    },

    # ── Jira: FRG-1002 (Bug fix) ───────────────────────────────────────────────
    {
        "source_type": "jira",
        "filename": "[seed] jira-FRG-1002-fix-queue-worker-crash.txt",
        "data": {
            "key": "FRG-1002",
            "project": "forge",
            "issue_type": "Bug",
            "summary": "Fix: email queue worker crash on null template variables",
            "status": "Resolved",
            "priority": "P1",
            "reporter": "rahul.sharma@forge.io",
            "labels": "notifications, bug, template-rendering, P1-followup",
            "description": """**Root cause of FRG-1001 incident.**

The notification queue worker uses Jinja2 to render templates like:
```
Your project "{{project.name}}" is due on {{project.due_date}}.
```

When `project.due_date` is `null` (projects with no due date set), the renderer raises `TemplateRenderException: NoneType is not iterable`. The worker does not catch this exception, crashes, and restarts — requeuing the same message → infinite crash loop.

**Fix:**
1. Wrap all template rendering in a try/except; on failure, use a safe fallback string
2. Add null coalescing for common nullable fields: `{{ project.due_date or "no due date" }}`
3. Add a `max_retries=3` poison-pill counter; after 3 failures, move to DLQ (see FRG-1003)

**PR:** forge-app/notifications-service#55
**Tests:** Added 12 unit tests covering null, missing, and malformed template variables.
""",
            "comments": [
                "dev.patel: Reviewing PR #55. LGTM on the null-safety changes. Left comments on the retry logic.",
                "rahul.sharma: Addressed all review comments. PR approved and merged.",
                "kenji.watanabe: Deployed to prod 2026-05-15 09:30 UTC. Monitoring queue depth — stable at <50 messages.",
            ],
        },
    },

    # ── Jira: FRG-1003 (Task: DLQ) ────────────────────────────────────────────
    {
        "source_type": "jira",
        "filename": "[seed] jira-FRG-1003-add-dead-letter-queue.txt",
        "data": {
            "key": "FRG-1003",
            "project": "forge",
            "issue_type": "Task",
            "summary": "Add dead-letter queue + alerting for notification failures",
            "status": "Resolved",
            "priority": "P2",
            "reporter": "rahul.sharma@forge.io",
            "labels": "notifications, reliability, DLQ, post-mortem-action-item",
            "description": """**Follow-up from FRG-1001 post-mortem.**

Currently, a failed message blocks the entire notification queue worker. We need:

1. **Dead-letter queue (DLQ):** Messages that fail 3 times are moved to a `notification_dlq` table rather than blocking the main queue. The DLQ is reviewed by ops daily.

2. **Queue depth alerting:** Add a Grafana alert that fires when `notification_queue.pending_count > 1000` for >2 minutes.

3. **DLQ monitoring dashboard:** New Grafana panel showing DLQ depth over time, with drill-down by failure reason.

**Implementation in:** forge-app/notifications-service#55 (same PR as FRG-1002).

**Acceptance criteria:**
- Worker processes up to 3 retries per message before DLQ
- Grafana alert fires in staging when depth >1000
- DLQ dashboard visible in Grafana → Notifications space
""",
            "comments": [
                "dev.patel: DLQ table migration + worker changes complete. Alert rule added.",
                "rahul.sharma: Dashboard looks great. Merging with FRG-1002 fix in PR #55.",
            ],
        },
    },

    # ── Slack: #incidents thread ──────────────────────────────────────────────
    {
        "source_type": "slack",
        "filename": "[seed] slack-incidents-notification-delivery-outage-2026-05-14.txt",
        "data": {
            "workspace": "forge-hq",
            "channel": "incidents",
            "channel_type": "public",
            "title": "Notification delivery outage — 2026-05-14 14:22 UTC",
            "participants": "aisha.okonkwo, rahul.sharma, dev.patel, sofia.chen, kenji.watanabe, marcus.webb",
            "labels": "P1, notifications, incident",
            "linked_jira_tickets": "FRG-1001, FRG-1002, FRG-1003",
            "linked_github_prs": "forge-app/notifications-service#55",
            "messages": [
                "aisha.okonkwo: 🚨 INCIDENT — Notification queue workers are crash-looping. PagerDuty fired. Queue depth at 8,000 and climbing. Taking IC role.",
                "rahul.sharma: On it. Pulling logs now. What triggered the spike?",
                "aisha.okonkwo: Looks like a bulk send from Vertex Analytics — 12,400 messages in one shot.",
                "dev.patel: Queue depth now 23,000. Workers are restarting every ~45 seconds.",
                "rahul.sharma: Found it. Template variable `project.due_date` is null for some of their projects. Jinja2 blows up on null, worker crashes, message gets requeued → infinite loop.",
                "kenji.watanabe: Can we just restart and skip the bad messages?",
                "rahul.sharma: Working on a script to identify and move malformed messages to DEAD_LETTER. 10 min.",
                "marcus.webb: Keeping exec leadership informed. Sofia, can you loop in Vertex Analytics CSM?",
                "sofia.chen: On it. Calling their VP Eng now.",
                "rahul.sharma: Malformed messages moved to DEAD_LETTER (1,247 messages). Queue starting to drain.",
                "aisha.okonkwo: ✅ Queue depth falling. New notifications delivering. ETA for full backlog clearance: ~3 hours.",
                "dev.patel: Fix is in PR #55 — forge-app/notifications-service#55. Null-safe template rendering + DLQ. Reviewing now.",
                "sofia.chen: Vertex VP Eng acknowledged. They're okay with 15-day service credit. CSM note in HubSpot.",
                "aisha.okonkwo: ✅ RESOLVED — 18:45 UTC. 47,000 messages redelivered. FRG-1001 closed. FRG-1002/1003 fix in PR #55 deploying tomorrow.",
                "rahul.sharma: Post-mortem written in Confluence: Post-Mortem: FRG-1001 Notification Delivery Outage — 2026-05-14",
            ],
        },
    },

    # ── GitHub: PR #55 ────────────────────────────────────────────────────────
    {
        "source_type": "github",
        "filename": "[seed] github-forge-app-notifications-service-pr-55.txt",
        "data": {
            "repo": "forge-app/notifications-service",
            "type": "pull_request",
            "number": 55,
            "title": "Fix queue worker crash on null template vars + add dead-letter queue",
            "state": "merged",
            "author": "rahul.sharma",
            "base_branch": "main",
            "labels": "bug-fix, reliability, P1-followup",
            "files_changed": (
                "src/workers/notification_worker.py, "
                "src/template/renderer.py, "
                "src/models/notification_dlq.py, "
                "migrations/0047_add_notification_dlq.py, "
                "infra/grafana/notifications_dashboard.json, "
                "tests/test_template_renderer.py, "
                "tests/test_notification_worker.py"
            ),
            "linked_issues": "FRG-1002, FRG-1003",
            "body": """## Summary

Fixes the P1 notification outage (FRG-1001) by addressing two root causes:

### 1. Null-safe template rendering (FRG-1002)

`renderer.py` now handles `null` / `None` template variables gracefully:
```python
# Before
env.from_string(template).render(**vars)  # crashes if any var is None

# After
safe_vars = {k: (v if v is not None else "") for k, v in vars.items()}
try:
    return env.from_string(template).render(**safe_vars)
except TemplateRenderException as e:
    logger.warning("Template render failed for msg %s: %s", msg_id, e)
    return None  # triggers DLQ path
```

### 2. Dead-letter queue (FRG-1003)

- New `notification_dlq` table (migration `0047`)
- Worker moves messages to DLQ after 3 consecutive failures
- Grafana alert: queue depth >1000 for >2 min → PagerDuty
- New Grafana dashboard panel: DLQ depth over time

### Testing

- 12 new unit tests for null, missing, and malformed template variables
- 4 integration tests for DLQ path
- Tested in staging with a replay of the Vertex Analytics batch (all 12,400 messages processed, 0 crashes)

### Deployment

```bash
# Run migration first
python manage.py migrate 0047_add_notification_dlq

# Rolling restart (no downtime)
kubectl rollout restart deployment/notification-worker -n forge-prod
```
""",
            "comments": [
                "dev.patel: LGTM. One suggestion: add a metric counter for DLQ entries so we can alert on rate-of-DLQ as well as depth.",
                "rahul.sharma: Good call. Added `notification_dlq_rate` counter. Updated dashboard.",
                "kenji.watanabe: Migration tested in staging. No issues. Approved.",
                "dev.patel: Approved. Merging.",
            ],
        },
    },

    # ── HubSpot: Vertex Analytics ─────────────────────────────────────────────
    {
        "source_type": "hubspot",
        "filename": "[seed] hubspot-vertex-analytics.txt",
        "data": {
            "company_name": "Vertex Analytics",
            "company_domain": "vertexanalytics.com",
            "stage": "customer",
            "account_tier": "enterprise",
            "industry": "data_analytics",
            "interested_products": "forge-projects, forge-support, forge-crm",
            "notes": """Vertex Analytics is a 3-year enterprise customer using Forge as their primary project management and internal CRM platform. ~420 seats. Contract value: $180,000/yr. Renews 2026-11-01.

**2026-05-14 INCIDENT NOTE (Sofia Chen):** Vertex triggered the P1 notification outage (FRG-1001) by sending a bulk project deadline reminder batch with null due_date values. This caused Forge's notification worker to crash-loop for 4h 23min, blocking notifications for all customers, not just Vertex.

Their VP Engineering (James Park, jpark@vertexanalytics.com) called to escalate. He was frustrated but professional — acknowledged their own bulk API usage was unusually large. We offered a 15-day service credit (~$7,400) which he accepted.

**Action items from this incident:**
- Forge to implement bulk API rate limiting (FRG-1004, Kenji Watanabe, due 2026-06-07)
- Vertex to review their batch job scheduling (they were sending 12,400 messages in one API call at 14:22 UTC)
- Quarterly business review scheduled for 2026-06-15 to discuss API usage patterns

**Renewal risk:** LOW. James was satisfied with incident response speed and communication. SLA was technically breached (4h 23min > 4h P1 SLA) but only by 23 minutes. Legal reviewing whether service credit satisfies SLA breach clause.
""",
            "next_step": "QBR on 2026-06-15. Discuss bulk API usage patterns and rate limiting rollout.",
            "blockers": [
                "Legal review of SLA breach clause still pending",
                "FRG-1004 (bulk API rate limiting) not yet shipped — Vertex must be notified before it goes live",
            ],
        },
    },

]
