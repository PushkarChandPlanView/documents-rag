export type Jira       = { source: "jira";       key: string; project: string; issueType: string; status: string;  summary: string; description: string };
export type Confluence = { source: "confluence"; key: string; space: string;   pageId: string;   title: string;   content: string     };
export type Github     = { source: "github";     key: string; repo: string;    issueId: string;  title: string;   content: string     };
export type Slack      = { source: "slack";      key: string; channel: string; user: string;     content: string                     };
export type Link       = { source: "link";       key: string; url: string;     title: string;    description: string                 };

export type Source    = "jira" | "confluence" | "github" | "slack" | "link" | null;
export type QueueItem = Jira | Confluence | Github | Slack | Link;
