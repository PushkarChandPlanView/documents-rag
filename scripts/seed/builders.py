"""
Text builders for each source type.

Mirrors the JS buildXxxText() functions in ingest.html exactly so the
plain-text output is in the same format the embedding pipeline already knows.
"""


def build_jira_text(d: dict) -> str:
    lines = [
        f"JIRA ISSUE: {d['key']}",
        f"Project: {d.get('project', '')}",
        f"Type: {d.get('issue_type', 'Task')}",
        f"Summary: {d['summary']}",
    ]
    meta_parts = []
    if d.get("status"):
        meta_parts.append(f"Status: {d['status']}")
    if d.get("priority"):
        meta_parts.append(f"Priority: {d['priority']}")
    if d.get("reporter"):
        meta_parts.append(f"Reporter: {d['reporter']}")
    if meta_parts:
        lines.append("   ".join(meta_parts))
    if d.get("labels"):
        lines.append(f"Labels: {d['labels']}")
    lines.append("")
    lines.append("Description:")
    lines.append(d.get("description", ""))
    if d.get("comments"):
        lines.append("")
        lines.append("Comments:")
        for c in d["comments"]:
            lines.append(c)
    return "\n".join(lines)


def build_confluence_text(d: dict) -> str:
    meta_parts = []
    if d.get("space"):
        meta_parts.append(f"Space: {d['space']}")
    if d.get("author"):
        meta_parts.append(f"Author: {d['author']}")
    if d.get("status"):
        meta_parts.append(f"Status: {d['status']}")
    if d.get("confidentiality"):
        meta_parts.append(f"Confidentiality: {d['confidentiality']}")
    lines = [
        f"CONFLUENCE PAGE: {d['title']}",
        "   ".join(meta_parts),
    ]
    if d.get("labels"):
        lines.append(f"Labels: {d['labels']}")
    lines.append("")
    lines.append(d.get("content", ""))
    return "\n".join(lines)


def build_slack_text(d: dict) -> str:
    channel_type = d.get("channel_type", "public")
    lines = [
        f"SLACK THREAD: {d['title']}",
        f"Workspace: {d.get('workspace', '')}   Channel: #{d['channel']} ({channel_type})",
    ]
    if d.get("participants"):
        lines.append(f"Participants: {d['participants']}")
    if d.get("labels"):
        lines.append(f"Labels: {d['labels']}")
    if d.get("linked_jira_tickets"):
        lines.append(f"Linked Jira: {d['linked_jira_tickets']}")
    if d.get("linked_github_prs"):
        lines.append(f"Linked PRs: {d['linked_github_prs']}")
    lines.append("")
    lines.append("Messages:")
    for msg in d.get("messages", []):
        lines.append(msg)
    return "\n".join(lines)


def build_hubspot_text(d: dict) -> str:
    meta_parts = []
    if d.get("company_domain"):
        meta_parts.append(f"Domain: {d['company_domain']}")
    if d.get("stage"):
        meta_parts.append(f"Stage: {d['stage']}")
    if d.get("account_tier"):
        meta_parts.append(f"Tier: {d['account_tier']}")
    if d.get("industry"):
        meta_parts.append(f"Industry: {d['industry']}")
    lines = [
        f"HUBSPOT ACCOUNT: {d['company_name']}",
        "   ".join(meta_parts),
    ]
    if d.get("interested_products"):
        lines.append(f"Products: {d['interested_products']}")
    lines.append("")
    lines.append("Notes:")
    lines.append(d.get("notes", ""))
    if d.get("next_step"):
        lines.append("")
        lines.append(f"Next Step: {d['next_step']}")
    if d.get("blockers"):
        lines.append("")
        lines.append("Blockers:")
        for b in d["blockers"]:
            lines.append(b)
    return "\n".join(lines)


def build_github_text(d: dict) -> str:
    item_type = d.get("type", "pull_request").upper()
    meta_parts = []
    if d.get("state"):
        meta_parts.append(f"State: {d['state']}")
    if d.get("author"):
        meta_parts.append(f"Author: {d['author']}")
    if d.get("base_branch"):
        meta_parts.append(f"Base: {d['base_branch']}")
    lines = [
        f"GITHUB {item_type}: {d['repo']}#{d['number']}",
        f"Title: {d['title']}",
        "   ".join(meta_parts),
    ]
    if d.get("labels"):
        lines.append(f"Labels: {d['labels']}")
    if d.get("files_changed"):
        lines.append(f"Files Changed: {d['files_changed']}")
    if d.get("linked_issues"):
        lines.append(f"Linked Issues: {d['linked_issues']}")
    lines.append("")
    lines.append("Description:")
    lines.append(d.get("body", ""))
    if d.get("comments"):
        lines.append("")
        lines.append("Comments:")
        for c in d["comments"]:
            lines.append(c)
    return "\n".join(lines)
