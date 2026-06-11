import { useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import {
  Toolbar,
  ToolbarSectionLeft,
  ToolbarSectionRight,
  ToolbarButtonEmpty,
} from "@planview/pv-toolbar";
import { ButtonPrimary, ButtonEmpty, ButtonDestructive, Chip } from "@planview/pv-uikit";
import { color as pvColor } from "@planview/pv-utilities";
import { AiAnvi, Plus, Edit, Trash, History } from "@planview/pv-icons";
import { useAgents, useDeleteAgent } from "@/hooks/useAgents";
import { AgentFormModal } from "@/components/agents/AgentFormModal";
import { RunDrawer } from "@/components/agents/RunDrawer";
import { RunsPanel } from "@/components/agents/RunsPanel";
import type { Agent } from "@/types/agent";

// ── Styles ────────────────────────────────────────────────────────────────────

const PageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: hidden;
`;

const ContentArea = styled.div`
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
`;

const AgentList = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${spacing.large}px;
  display: flex;
  flex-direction: column;
  gap: ${spacing.medium}px;
`;

const Card = styled.div<{ $selected?: boolean }>`
  background: ${color.backgroundNeutral0};
  border: 1px solid ${({ $selected }) => ($selected ? color.borderActive ?? "#1565c0" : color.borderLight)};
  border-radius: 8px;
  padding: ${spacing.medium}px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-shadow: ${({ $selected }) =>
    $selected ? "0 0 0 2px rgba(21,101,192,0.18)" : "none"};
  &:hover {
    border-color: ${color.borderActive ?? "#1565c0"};
  }
`;

const CardHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: ${spacing.xsmall}px;
`;

const AgentName = styled.div`
  ${text.regularSemibold}
  color: ${color.textPrimary};
`;

const AgentDescription = styled.div`
  ${text.small}
  color: ${color.textSecondary};
  line-height: 1.55;
  margin-bottom: ${spacing.small}px;
`;

const MetaRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${spacing.xsmall}px;
  align-items: center;
  margin-bottom: ${spacing.small}px;
`;

const ToolBadge = styled.span`
  font-size: 10px;
  background: #e3f2fd;
  color: #1565c0;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
`;

const MetaDot = styled.span`
  color: ${color.borderLight};
`;

const MetaText = styled.span`
  ${text.small}
  color: ${color.textSecondary};
`;

const CardActions = styled.div`
  display: flex;
  gap: ${spacing.small}px;
  align-items: center;
`;

const LastRun = styled.span`
  ${text.small}
  color: ${color.textSecondary};
  margin-left: auto;
`;

const ToolbarTitle = styled.span`
  ${text.small};
  font-weight: 700;
`;

const EmptyState = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: ${spacing.medium}px;
  color: ${color.textSecondary};
`;

const EmptyTitle = styled.div`
  ${text.regularSemibold}
  color: ${color.textPrimary};
`;

const EmptyBody = styled.div`
  ${text.small}
  color: ${color.textSecondary};
  text-align: center;
  max-width: 360px;
`;

// ── Types ─────────────────────────────────────────────────────────────────────

type SidePanelMode = "run" | "history";

// ── Component ─────────────────────────────────────────────────────────────────

export default function Agents() {
  const { data: agents = [], isLoading } = useAgents();
  const { mutate: deleteAgent } = useDeleteAgent();

  const [showCreate, setShowCreate] = useState(false);
  const [editAgent, setEditAgent] = useState<Agent | null>(null);
  const [sideAgent, setSideAgent] = useState<Agent | null>(null);
  const [sideMode, setSideMode] = useState<SidePanelMode>("run");
  // pre-filled query when re-running from history
  const [reRunQuery, setReRunQuery] = useState<string | undefined>(undefined);

  function openRun(agent: Agent) {
    setSideAgent((prev) => (prev?.id === agent.id && sideMode === "run" ? null : agent));
    setSideMode("run");
    setReRunQuery(undefined);
  }

  function openHistory(agent: Agent, e: React.MouseEvent) {
    e.stopPropagation();
    setSideAgent((prev) => (prev?.id === agent.id && sideMode === "history" ? null : agent));
    setSideMode("history");
  }

  function handleReRun(query: string) {
    setReRunQuery(query);
    setSideMode("run");
  }

  function handleDelete(agent: Agent, e: React.MouseEvent) {
    e.stopPropagation();
    if (confirm(`Delete agent "${agent.name}"? This cannot be undone.`)) {
      deleteAgent(agent.id);
      if (sideAgent?.id === agent.id) setSideAgent(null);
    }
  }

  function closePanel() {
    setSideAgent(null);
    setReRunQuery(undefined);
  }

  return (
    <PageWrapper>
      <Toolbar label="Agents toolbar">
        <ToolbarSectionLeft>
          <ToolbarTitle>Agents</ToolbarTitle>
        </ToolbarSectionLeft>
        <ToolbarSectionRight moreMenuLabel="More actions">
          <ToolbarButtonEmpty
            icon={<Plus />}
            tooltip="New agent"
            onClick={() => setShowCreate(true)}
          />
        </ToolbarSectionRight>
      </Toolbar>

      <ContentArea>
        <AgentList>
          {isLoading && (
            <div style={{ fontSize: 13, color: color.textSecondary, padding: spacing.medium }}>
              Loading agents…
            </div>
          )}

          {!isLoading && agents.length === 0 && (
            <EmptyState>
              <AiAnvi style={{ fontSize: 48, opacity: 0.3 }} />
              <EmptyTitle>No agents yet</EmptyTitle>
              <EmptyBody>
                Create an agent to research documents across your connected sources and
                generate structured answers.
              </EmptyBody>
              <ButtonPrimary icon={<Plus />} onClick={() => setShowCreate(true)}>
                New agent
              </ButtonPrimary>
            </EmptyState>
          )}

          {agents.map((agent) => {
            const isSelected = sideAgent?.id === agent.id;
            return (
              <Card
                key={agent.id}
                $selected={isSelected}
                onClick={() => openRun(agent)}
              >
                <CardHeader>
                  <AgentName>{agent.name}</AgentName>
                  <Chip color={pvColor.success100} label="Active" disabled />
                </CardHeader>

                <MetaRow>
                  {agent.tools.map((t) => (
                    <ToolBadge key={t}>{t}</ToolBadge>
                  ))}
                  <MetaDot>·</MetaDot>
                  <MetaText>Output: {agent.output_format}</MetaText>
                  <MetaDot>·</MetaDot>
                  <MetaText>Max {agent.max_iter} iterations</MetaText>
                </MetaRow>

                {agent.description && (
                  <AgentDescription>{agent.description}</AgentDescription>
                )}

                <CardActions onClick={(e) => e.stopPropagation()}>
                  <ButtonPrimary
                    icon={<AiAnvi />}
                    onClick={() => openRun(agent)}
                  >
                    Run
                  </ButtonPrimary>
                  <ButtonEmpty
                    icon={<History />}
                    onClick={(e) => openHistory(agent, e)}
                    tooltip="View run history"
                  >
                    History
                  </ButtonEmpty>
                  <ButtonEmpty
                    icon={<Edit />}
                    onClick={(e) => { e.stopPropagation(); setEditAgent(agent); }}
                  >
                    Edit
                  </ButtonEmpty>
                  <ButtonDestructive
                    icon={<Trash />}
                    onClick={(e) => handleDelete(agent, e)}
                  >
                    Delete
                  </ButtonDestructive>
                  <LastRun>
                    {agent.updated_at
                      ? `Updated ${new Date(agent.updated_at).toLocaleDateString()}`
                      : ""}
                  </LastRun>
                </CardActions>
              </Card>
            );
          })}
        </AgentList>

        {sideAgent && sideMode === "run" && (
          <RunDrawer
            key={`${sideAgent.id}-${reRunQuery ?? ""}`}
            agent={sideAgent}
            initialQuery={reRunQuery}
            onClose={closePanel}
          />
        )}
        {sideAgent && sideMode === "history" && (
          <RunsPanel
            agent={sideAgent}
            onClose={closePanel}
            onReRun={handleReRun}
          />
        )}
      </ContentArea>

      {showCreate && (
        <AgentFormModal onClose={() => setShowCreate(false)} />
      )}
      {editAgent && (
        <AgentFormModal agent={editAgent} onClose={() => setEditAgent(null)} />
      )}
    </PageWrapper>
  );
}
