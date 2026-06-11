import { CustomSlackIcon } from "@/customicons/slack";
import { Community, FlowMetricsVelocity, Link as LinkIcon, Workspace } from "@planview/pv-icons";
import React from "react";
import styled from "styled-components";
import type { QueueItem, Source } from "./types";

export const JiraIcon = styled(FlowMetricsVelocity)`rotate: -45deg;`;

export const SOURCE_ICON: Record<NonNullable<Source>, React.ReactElement> = {
  jira:       <JiraIcon />,
  confluence: <Workspace />,
  github:     <Community />,
  slack:      <CustomSlackIcon />,
  link:       <LinkIcon />,
};

export const SOURCE_HEADER: Record<NonNullable<Source>, { title: string; subtitle: string }> = {
  jira:       { title: "Configure Jira Source",       subtitle: "Paste issue details to parse and index."       },
  confluence: { title: "Configure Confluence Source", subtitle: "Paste page details to parse and index."        },
  github:     { title: "Configure GitHub Source",     subtitle: "Paste issue or PR details to parse and index." },
  slack:      { title: "Configure Slack Source",      subtitle: "Paste message details to parse and index."     },
  link:       { title: "Configure Link Source",       subtitle: "Paste a URL to fetch and index."               },
};

export const SOURCE_LABEL: Record<NonNullable<Source>, string> = {
  jira:       "Jira Issue",
  confluence: "Confluence",
  github:     "GitHub Issue",
  slack:      "Slack Message",
  link:       "Link",
};

export function getItemMeta(item: QueueItem): string {
  const type = SOURCE_LABEL[item.source];
  switch (item.source) {
    case "jira":       return `${type} • ${item.summary}`;
    case "confluence": return `${item.space ? item.space + " Space" : type} • ${item.title}`;
    case "github":     return `${type} • ${item.title}`;
    case "link":       return `${type} • ${item.title}`;
    case "slack":      return `${type} • #${item.channel}`;
  }
}
