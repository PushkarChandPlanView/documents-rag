import React, { useState } from "react";
import styled from "styled-components";
import { border, color, spacing, text } from "@planview/pv-utilities";
import { Checkbox } from "@planview/pv-uikit";
import { Community, FlowMetricsVelocity, Workspace } from "@planview/pv-icons";
import { CustomSlackIcon } from "@/customicons/slack";

// ── Source definitions ────────────────────────────────────────────────────────

const JiraIcon = styled(FlowMetricsVelocity)`rotate: -45deg;`;

const HubSpotIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M18.16 8.75V6.37a2.1 2.1 0 0 0 1.22-1.9V4.4a2.1 2.1 0 0 0-2.1-2.1h-.07a2.1 2.1 0 0 0-2.1 2.1v.07a2.1 2.1 0 0 0 1.22 1.9v2.38a5.96 5.96 0 0 0-2.83 1.24L7.2 5.78a2.34 2.34 0 1 0-.9 1.04l6.1 3.95a5.97 5.97 0 0 0-.84 3.08 5.97 5.97 0 0 0 .94 3.25l-1.85 1.85a1.8 1.8 0 1 0 1.06 1.06l1.8-1.8a5.97 5.97 0 0 0 3.7 1.27 5.99 5.99 0 1 0-1.05-11.93zm1.05 9.5a3.54 3.54 0 1 1 0-7.08 3.54 3.54 0 0 1 0 7.08z"/>
  </svg>
);

type SourceId = "slack" | "github" | "confluence" | "jira" | "hubspot";

interface SourceDef {
  id: SourceId;
  name: string;
  description: string;
  icon: React.ReactNode;
  category: string;
}

const SOURCES: SourceDef[] = [
  {
    id: "jira",
    name: "Jira",
    description: "Index issues, epics and project boards from Jira Software.",
    icon: <JiraIcon />,
    category: "Project Management",
  },
  {
    id: "confluence",
    name: "Confluence",
    description: "Index pages, spaces and knowledge-base articles from Confluence.",
    icon: <Workspace />,
    category: "Knowledge Base",
  },
  {
    id: "github",
    name: "GitHub",
    description: "Index issues, pull requests and repositories from GitHub.",
    icon: <Community />,
    category: "Version Control",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Index messages, threads and files from Slack channels.",
    icon: <CustomSlackIcon />,
    category: "Communication",
  },
  {
    id: "hubspot",
    name: "HubSpot",
    description: "Index contacts, deals, tickets and notes from HubSpot CRM.",
    icon: <HubSpotIcon />,
    category: "CRM",
  },
];

// ── Styled components ─────────────────────────────────────────────────────────

const PageWrapper = styled.div`
  padding: ${spacing.large}px;
`;

const PageHeader = styled.div`
  margin-bottom: ${spacing.large}px;
`;

const PageTitle = styled.h1`
  font-size: 20px;
  font-weight: 700;
  color: ${color.textPrimary};
  margin: 0 0 4px;
`;

const PageSub = styled.p`
  ${text.small};
  color: ${color.textSecondary};
  margin: 0;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: ${spacing.medium}px;
`;

const Card = styled.div<{ $enabled: boolean }>`
  ${({ $enabled }) => ($enabled ? border.normal : border.light)};
  border-radius: 10px;
  padding: ${spacing.medium}px;
  background: ${({ $enabled }) => ($enabled ? color.backgroundNeutral100 : color.backgroundNeutral50)};
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
  transition: border-color 0.15s ease, background 0.15s ease;
`;

const CardTop = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: ${spacing.small}px;
`;

const CardLeft = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.small}px;
`;

const IconBox = styled.div<{ $enabled: boolean }>`
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: ${({ $enabled }) => ($enabled ? color.blue200 : color.gray100)};
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  svg {
    width: 20px;
    height: 20px;
    color: ${({ $enabled }) => ($enabled ? color.blue400 : color.gray400)};
  }
`;

const SourceName = styled.div`
  font-size: 14px;
  font-weight: 600;
  color: ${color.textPrimary};
`;

const Category = styled.div`
  ${text.small};
  color: ${color.textSecondary};
`;

const Description = styled.p`
  ${text.small};
  color: ${color.textSecondary};
  margin: 0;
  line-height: 1.5;
`;

const StatusBadge = styled.span<{ $enabled: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: ${({ $enabled }) => ($enabled ? color.green400 : color.gray400)};
  text-transform: uppercase;
  letter-spacing: 0.04em;
  &::before {
    content: "";
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: ${({ $enabled }) => ($enabled ? color.green400 : color.gray300)};
  }
`;

// ── Component ─────────────────────────────────────────────────────────────────

const SourceConfig = () => {
  const [enabled, setEnabled] = useState<Record<SourceId, boolean>>({
    slack: false, github: false, confluence: false, jira: false, hubspot: false,
  });

  const toggle = (id: SourceId) =>
    setEnabled(prev => ({ ...prev, [id]: !prev[id] }));

  const enabledCount = Object.values(enabled).filter(Boolean).length;

  return (
    <PageWrapper>
      <PageHeader>
        <PageTitle>Data Sources</PageTitle>
        <PageSub>
          Enable the integrations you want to index.
          {enabledCount > 0 && ` ${enabledCount} of ${SOURCES.length} active.`}
        </PageSub>
      </PageHeader>

      <Grid>
        {SOURCES.map(({ id, name, description, icon, category }) => {
          const isEnabled = enabled[id];
          return (
            <Card key={id} $enabled={isEnabled}>
              <CardTop>
                <CardLeft>
                  <IconBox $enabled={isEnabled}>{icon}</IconBox>
                  <div>
                    <SourceName>{name}</SourceName>
                    <Category>{category}</Category>
                  </div>
                </CardLeft>
                <Checkbox
                  selected={isEnabled}
                  onChange={() => toggle(id)}
                  aria-label={`${isEnabled ? "Disable" : "Enable"} ${name}`}
                />
              </CardTop>
              <Description>{description}</Description>
              <StatusBadge $enabled={isEnabled}>
                {isEnabled ? "Active" : "Inactive"}
              </StatusBadge>
            </Card>
          );
        })}
      </Grid>
    </PageWrapper>
  );
};

export default SourceConfig;