import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { ButtonEmpty, ButtonPrimary } from "@planview/pv-uikit";
import { AiAnvi, CheckmarkCircleFilled, CrossCircleFilled } from "@planview/pv-icons";
import { useAgentRuns } from "@/hooks/useAgents";
import type { Agent } from "@/types/agent";
import { useState } from "react";

// ── Styles ────────────────────────────────────────────────────────────────────

const Panel = styled.aside`
  width: 560px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: ${color.backgroundNeutral0};
  border-left: 1px solid ${color.borderLight};
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.08);
`;

const PanelHeader = styled.div`
  height: 40px;
  padding: 0 ${spacing.medium}px;
  display: flex;
  align-items: center;
  gap: ${spacing.small}px;
  border-bottom: 1px solid ${color.borderLight};
  flex-shrink: 0;
`;

const PanelTitle = styled.span`
  ${text.smallSemibold}
  flex: 1;
`;

const TwoCol = styled.div`
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
`;

const RunsList = styled.div`
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid ${color.borderLight};
  overflow-y: auto;
  display: flex;
  flex-direction: column;
`;

const RunItem = styled.div<{ $active: boolean }>`
  padding: 10px 12px;
  border-bottom: 1px solid ${color.borderLight};
  cursor: pointer;
  background: ${({ $active }) => ($active ? "#e3f2fd" : "transparent")};
  &:hover { background: ${({ $active }) => ($active ? "#e3f2fd" : color.backgroundNeutral50)}; }
`;

const RunQuery = styled.div`
  font-size: 12px;
  color: ${color.textPrimary};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 2px;
`;

const RunMeta = styled.div`
  font-size: 10px;
  color: ${color.textSecondary};
  display: flex;
  gap: 6px;
  align-items: center;
`;

const StatusDot = styled.span<{ $status: string }>`
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
  background: ${({ $status }) =>
    $status === "completed" ? "#2e7d32"
    : $status === "failed" ? "#c62828"
    : "#ef6c00"};
`;

const RunDetail = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${spacing.medium}px;
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
`;

const EmptyDetail = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  ${text.small}
  color: ${color.textSecondary};
`;

const SubLabel = styled.div`
  ${text.small}
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: ${color.textSecondary};
  margin-bottom: 4px;
`;

const PlanStep = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid ${color.borderLight};
  font-size: 12px;
  color: ${color.textSecondary};
  &:last-child { border-bottom: none; }
`;

const AnswerBox = styled.div`
  background: #f5f8ff;
  border: 1px solid #c5d8f5;
  border-radius: 6px;
  padding: ${spacing.small}px ${spacing.medium}px;
  font-size: 12px;
  color: ${color.textPrimary};
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  min-height: 48px;
`;

const DocBanner = styled.div`
  background: #e8f5e9;
  border: 1px solid #c8e6c9;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #2e7d32;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const ErrorBanner = styled.div`
  background: #ffebee;
  border: 1px solid #ffcdd2;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #c62828;
`;

const PanelFooter = styled.div`
  padding: ${spacing.small}px ${spacing.medium}px;
  border-top: 1px solid ${color.borderLight};
  display: flex;
  gap: ${spacing.small}px;
  justify-content: flex-end;
`;

const EmptyRuns = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  ${text.small}
  color: ${color.textSecondary};
  padding: ${spacing.medium}px;
  text-align: center;
`;

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
    " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  agent: Agent;
  onClose: () => void;
  onReRun: (query: string) => void;
}

export function RunsPanel({ agent, onClose, onReRun }: Props) {
  const { data: runs = [], isLoading, refetch } = useAgentRuns(agent.id);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = runs.find((r) => r.id === selectedId) ?? null;

  return (
    <Panel>
      <PanelHeader>
        <AiAnvi />
        <PanelTitle>Run history — {agent.name}</PanelTitle>
        <ButtonEmpty
          icon={<CrossCircleFilled />}
          tooltip="Close"
          onClick={onClose}
          aria-label="Close runs panel"
        />
      </PanelHeader>

      <TwoCol>
        {/* Left: run list */}
        <RunsList>
          {isLoading && (
            <div style={{ padding: 12, fontSize: 12, color: color.textSecondary }}>Loading…</div>
          )}
          {!isLoading && runs.length === 0 && (
            <EmptyRuns>No runs yet for this agent.</EmptyRuns>
          )}
          {runs.map((run) => (
            <RunItem
              key={run.id}
              $active={run.id === selectedId}
              onClick={() => setSelectedId(run.id)}
            >
              <RunQuery title={run.query}>{run.query}</RunQuery>
              <RunMeta>
                <StatusDot $status={run.status} />
                {run.status}
                <span>·</span>
                {fmtDate(run.created_at)}
              </RunMeta>
            </RunItem>
          ))}
        </RunsList>

        {/* Right: run detail */}
        {!selected ? (
          <EmptyDetail>Select a run to see details</EmptyDetail>
        ) : (
          <RunDetail>
            <div style={{ fontSize: 11, color: color.textSecondary, fontStyle: "italic" }}>
              "{selected.query}"
            </div>
            <RunMeta style={{ gap: 6 }}>
              <StatusDot $status={selected.status} />
              {selected.status}
              <span>·</span>
              {fmtDate(selected.created_at)}
              {selected.completed_at && (
                <>
                  <span>→</span>
                  {fmtDate(selected.completed_at)}
                </>
              )}
            </RunMeta>

            {selected.plan && selected.plan.length > 0 && (
              <>
                <SubLabel>Plan ({selected.plan.length} steps)</SubLabel>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {selected.plan.map((step, i) => (
                    <PlanStep key={i}>
                      <span style={{ color: "#2e7d32", fontWeight: 700, flexShrink: 0 }}>✓</span>
                      <span>{step}</span>
                    </PlanStep>
                  ))}
                </div>
              </>
            )}

            {selected.status === "running" && (
              <AnswerBox style={{ color: color.textSecondary }}>
                Run is still in progress…
              </AnswerBox>
            )}

            {selected.status === "failed" && (
              <ErrorBanner>Run failed. Check agent_service logs for details.</ErrorBanner>
            )}

            {selected.result_document_id && (
              <DocBanner>
                <CheckmarkCircleFilled />
                Result document saved —{" "}
                <a
                  href="/documents"
                  style={{ color: "#1565c0", textDecoration: "underline", fontSize: 11 }}
                >
                  Manage ↗
                </a>
              </DocBanner>
            )}
          </RunDetail>
        )}
      </TwoCol>

      <PanelFooter>
        <ButtonEmpty onClick={() => void refetch()}>Refresh</ButtonEmpty>
        {selected && (
          <ButtonPrimary
            icon={<AiAnvi />}
            onClick={() => {
              onReRun(selected.query);
              onClose();
            }}
          >
            Re-run this query
          </ButtonPrimary>
        )}
      </PanelFooter>
    </Panel>
  );
}
