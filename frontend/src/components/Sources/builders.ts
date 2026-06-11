/** Mirror of ingest.html buildXxxText() functions — produces plain-text documents. */

export function buildJiraText(d: Record<string, string>): string {
  const lines = [
    `JIRA ISSUE: ${d.key}`,
    `Project: ${d.project}`,
    `Type: ${d.issue_type || d.issueType}   Status: ${d.status}   Priority: ${d.priority || "P2"}`,
    d.reporter ? `Reporter: ${d.reporter}` : "",
    "",
    `Summary: ${d.summary}`,
    "",
    "Description:",
    d.description || "",
  ];
  if (d.labels) lines.push("", `Labels: ${d.labels}`);
  if (d.comments) {
    lines.push("", "Comments:");
    d.comments.split("\n").forEach((c) => c.trim() && lines.push(`  ${c.trim()}`));
  }
  return lines.filter((l) => l !== undefined).join("\n").trim();
}

export function buildConfluenceText(d: Record<string, string>): string {
  const lines = [
    `CONFLUENCE PAGE: ${d.title}`,
    `Space: ${d.space}   Author: ${d.author || "unknown"}   Status: ${d.status || "published"}   Confidentiality: ${d.confidentiality || "internal"}`,
    "",
    d.content || "",
  ];
  if (d.labels) lines.push("", `Labels: ${d.labels}`);
  return lines.join("\n").trim();
}

export function buildHubspotText(d: Record<string, string>): string {
  const lines = [
    `HUBSPOT ACCOUNT: ${d.company_name}`,
    `Domain: ${d.company_domain}   Stage: ${d.stage || "lead"}   Tier: ${d.account_tier || "startup"}   Industry: ${d.industry || ""}`,
    "",
    d.notes ? `Notes:\n${d.notes}` : "",
  ];
  if (d.contacts) lines.push("", `Contacts: ${d.contacts}`);
  if (d.open_deals) lines.push(`Open Deals: ${d.open_deals}`);
  if (d.labels) lines.push("", `Labels: ${d.labels}`);
  return lines.join("\n").trim();
}

export function buildSlackText(d: Record<string, string>): string {
  const lines = [
    `SLACK THREAD: ${d.title}`,
    `Workspace: ${d.workspace}   Channel: #${d.channel} (${d.channel_type || "public"})`,
  ];
  if (d.participants) lines.push(`Participants: ${d.participants}`);
  lines.push("", "Messages:");
  (d.messages || "").split("\n").forEach((m) => m.trim() && lines.push(`  ${m.trim()}`));
  if (d.linked_jira_tickets) lines.push("", `Linked Jira: ${d.linked_jira_tickets}`);
  if (d.linked_github_prs) lines.push(`Linked PRs: ${d.linked_github_prs}`);
  if (d.labels) lines.push("", `Labels: ${d.labels}`);
  return lines.join("\n").trim();
}

export function buildGithubText(d: Record<string, string>): string {
  const kind = (d.type || "pull_request").toUpperCase().replace("_", " ");
  const lines = [
    `GITHUB ${kind}: ${d.repo}#${d.number}`,
    `Title: ${d.title}`,
    `State: ${d.state || "open"}   Author: ${d.author || ""}   Base: ${d.base_branch || "main"}`,
    "",
    "Description:",
    d.body || "",
  ];
  if (d.labels) lines.push("", `Labels: ${d.labels}`);
  if (d.files_changed) lines.push("", `Files changed: ${d.files_changed}`);
  if (d.comments) {
    lines.push("", "Comments:");
    d.comments.split("\n").forEach((c) => c.trim() && lines.push(`  ${c.trim()}`));
  }
  return lines.join("\n").trim();
}

export type SourceType = "jira" | "confluence" | "hubspot" | "slack" | "github";

const BUILDERS: Record<SourceType, (d: Record<string, string>) => string> = {
  jira: buildJiraText,
  confluence: buildConfluenceText,
  hubspot: buildHubspotText,
  slack: buildSlackText,
  github: buildGithubText,
};

const FILE_NAMES: Record<SourceType, (d: Record<string, string>) => string> = {
  jira:       (d) => `jira-${d.key || d.summary?.slice(0, 20) || "issue"}.txt`,
  confluence: (d) => `confluence-${d.space}-${d.title?.slice(0, 30) || "page"}.txt`,
  hubspot:    (d) => `hubspot-${d.company_domain || d.company_name || "account"}.txt`,
  slack:      (d) => `slack-${d.channel}-${d.title?.slice(0, 30) || "thread"}.txt`,
  github:     (d) => `github-${(d.repo || "repo").replace("/", "_")}-${d.number || "0"}.txt`,
};

/** Build a File ready for upload from source form data. */
export function buildFile(sourceType: SourceType, data: Record<string, string>): File {
  const text = BUILDERS[sourceType](data);
  const name = FILE_NAMES[sourceType](data);
  return new File([text], name, { type: "text/plain" });
}
