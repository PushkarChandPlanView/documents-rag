import { useCallback, useRef, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { ButtonEmpty, ButtonPrimary } from "@planview/pv-uikit";
import { Input } from "@planview/pv-uikit";
import { AiAnvi, CheckmarkCircleFilled, CrossCircleFilled } from "@planview/pv-icons";
import { agentsApi } from "@/api/agents";
import { useAuthStore } from "@/store/authStore";
import type { Agent, PlanviewResult } from "@/types/agent";

// ── Styles ────────────────────────────────────────────────────────────────────

const Drawer = styled.aside`
  width: 420px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: ${color.backgroundNeutral0};
  border-left: 1px solid ${color.borderLight};
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.08);
`;

const DrawerHeader = styled.div`
  height: 40px;
  padding: 0 ${spacing.medium}px;
  display: flex;
  align-items: center;
  gap: ${spacing.small}px;
  border-bottom: 1px solid ${color.borderLight};
  flex-shrink: 0;
`;

const DrawerTitle = styled.span`
  ${text.smallSemibold}
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const DrawerBody = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${spacing.medium}px;
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
`;

const DrawerFooter = styled.div`
  padding: ${spacing.small}px ${spacing.medium}px;
  border-top: 1px solid ${color.borderLight};
  display: flex;
  gap: ${spacing.small}px;
  justify-content: flex-end;
`;

const QueryRow = styled.div`
  display: flex;
  gap: ${spacing.small}px;
  align-items: flex-start;
`;

const SubLabel = styled.div`
  ${text.small}
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: ${color.textSecondary};
  margin-bottom: 4px;
`;

const PlanList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

const PlanStep = styled.div<{ $state: "pending" | "running" | "done" | "error" }>`
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid ${color.borderLight};
  font-size: 12px;
  color: ${({ $state }) =>
    $state === "running"
      ? color.textLinkNormal
      : $state === "done"
      ? color.textSuccess
      : $state === "error"
      ? "#c62828"
      : color.textSecondary};
  &:last-child { border-bottom: none; }
`;

const StepDot = styled.div<{ $state: "pending" | "running" | "done" | "error" }>`
  width: 16px;
  height: 16px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 1px;
  background: ${({ $state }) =>
    $state === "running" ? "#e3f2fd"
    : $state === "done"  ? "#e8f5e9"
    : $state === "error" ? "#ffebee"
    : "#f0f0f0"};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  color: ${({ $state }) =>
    $state === "running" ? "#1565c0"
    : $state === "done"  ? "#2e7d32"
    : $state === "error" ? "#c62828"
    : "#aaa"};
  animation: ${({ $state }) => ($state === "running" ? "pulseDot 1s ease-in-out infinite" : "none")};
  @keyframes pulseDot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
`;

const SourceBadge = styled.span`
  font-size: 10px;
  background: #e3f2fd;
  color: #0d47a1;
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 600;
  margin-left: 4px;
`;

const ChunksNote = styled.span`
  font-size: 10px;
  color: ${color.textSecondary};
  margin-left: 4px;
`;

const GeneratingRow = styled.div`
  font-size: 12px;
  color: ${color.textSecondary};
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  animation: fadePulse 1.4s ease-in-out infinite;
  @keyframes fadePulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.45; }
  }
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
  min-height: 60px;
`;

const SuccessBanner = styled.div`
  background: #e8f5e9;
  border: 1px solid #c8e6c9;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #2e7d32;
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const PlanviewBanner = styled.div`
  background: #f3e5f5;
  border: 1px solid #ce93d8;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 12px;
  color: #4a148c;
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const PlanviewStat = styled.span`
  font-size: 11px;
  color: #6a1b9a;
  font-weight: 600;
`;

const SuccessLinks = styled.div`
  display: flex;
  gap: 10px;
  margin-top: 2px;
`;

const DocLink = styled.a`
  font-size: 11px;
  color: #1565c0;
  text-decoration: underline;
  cursor: pointer;
`;

// ── Types ─────────────────────────────────────────────────────────────────────

type StepState = "pending" | "running" | "done" | "error";

interface PlanStepData {
  text: string;
  state: StepState;
  sources: string[];
  chunks?: number;
}

type DrawerView = "idle" | "running" | "generating" | "done" | "error";

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  agent: Agent;
  onClose: () => void;
  initialQuery?: string;
}

export function RunDrawer({ agent, onClose, initialQuery }: Props) {
  const { userEmail } = useAuthStore();
  const [query, setQuery] = useState(initialQuery ?? "");
  const [view, setView] = useState<DrawerView>("idle");
  const [planSteps, setPlanSteps] = useState<PlanStepData[]>([]);
  const [answer, setAnswer] = useState("");
  const [resultDocId, setResultDocId] = useState<string | null>(null);
  const [planviewResult, setPlanviewResult] = useState<PlanviewResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const startRun = useCallback(async () => {
    if (!query.trim()) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setView("running");
    setPlanSteps([]);
    setAnswer("");
    setResultDocId(null);
    setPlanviewResult(null);
    setErrorMsg("");

    try {
      const stream = agentsApi.streamRun(
        agent.id,
        query.trim(),
        userEmail ?? "",
        ctrl.signal
      );

      for await (const event of stream) {
        switch (event.type) {
          case "plan":
            setPlanSteps(
              event.steps.map((s) => ({ text: s, state: "pending", sources: [] }))
            );
            // mark first step as running
            setPlanSteps((prev) =>
              prev.map((s, i) => (i === 0 ? { ...s, state: "running" } : s))
            );
            break;

          case "step_done":
            setPlanSteps((prev) =>
              prev.map((s, i) => {
                if (i === event.step) {
                  return {
                    ...s,
                    state: "done",
                    sources: event.source_types ?? [],
                    chunks: event.chunks_found,
                  };
                }
                // mark next step as running
                if (i === event.step + 1) {
                  return { ...s, state: "running" };
                }
                return s;
              })
            );
            break;

          case "generating":
            // all steps done — show generating state
            setPlanSteps((prev) =>
              prev.map((s) => (s.state === "running" ? { ...s, state: "done" } : s))
            );
            setView("generating");
            break;

          case "token":
            setView("running"); // back to running once tokens flow
            setAnswer((prev) => prev + event.content);
            break;

          case "uploaded":
            setResultDocId(event.document_id);
            break;

          case "planview_done":
            setPlanviewResult({
              board_id: event.board_id,
              board_name: event.board_name,
              activities: event.activities,
              total_cards: event.total_cards,
              errors: event.errors,
            });
            break;

          case "done":
            if (event.document_id) setResultDocId(event.document_id);
            setPlanSteps((prev) =>
              prev.map((s) => (s.state === "running" ? { ...s, state: "done" } : s))
            );
            setView("done");
            break;

          case "error":
            setErrorMsg(event.content);
            setPlanSteps((prev) =>
              prev.map((s) => (s.state === "running" ? { ...s, state: "error" } : s))
            );
            setView("error");
            break;
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setErrorMsg((err as Error).message ?? "Unknown error");
        setView("error");
      }
    }
  }, [agent.id, query, userEmail]);

  function resetRun() {
    abortRef.current?.abort();
    setView("idle");
    setQuery("");
    setPlanSteps([]);
    setAnswer("");
    setResultDocId(null);
    setPlanviewResult(null);
    setErrorMsg("");
  }

  const isActive = view === "running" || view === "generating" || view === "done";

  return (
    <Drawer>
      <DrawerHeader>
        <AiAnvi />
        <DrawerTitle>Run — {agent.name}</DrawerTitle>
        <ButtonEmpty
          icon={<CrossCircleFilled />}
          tooltip="Close"
          onClick={onClose}
          aria-label="Close run drawer"
        />
      </DrawerHeader>

      <DrawerBody>
        {/* ── IDLE ── */}
        {view === "idle" && (
          <>
            <div style={{ fontSize: 12, color: "#555", lineHeight: 1.5 }}>
              Enter a query and run the agent. It will plan its search steps,
              retrieve context from connected sources, and stream an answer.
            </div>
            <QueryRow>
              <div style={{ flex: 1 }}>
                <Input
                  id="run-query"
                  value={query}
                  onChange={(v: string) => setQuery(v)}
                  placeholder="e.g. Summarize the notification P1 incident"
                />
              </div>
              <ButtonPrimary onClick={startRun} disabled={!query.trim()}>
                Run
              </ButtonPrimary>
            </QueryRow>
          </>
        )}

        {/* ── RUNNING / GENERATING / DONE ── */}
        {isActive && (
          <>
            {/* Query recap */}
            <div style={{ fontSize: 11, color: color.textSecondary, fontStyle: "italic" }}>
              "{query}"
            </div>

            {/* Plan checklist */}
            {planSteps.length > 0 && (
              <>
                <SubLabel>Plan</SubLabel>
                <PlanList>
                  {planSteps.map((s, i) => (
                    <PlanStep key={i} $state={s.state}>
                      <StepDot $state={s.state}>
                        {s.state === "done" ? "✓"
                         : s.state === "running" ? "…"
                         : s.state === "error" ? "✗"
                         : "○"}
                      </StepDot>
                      <span style={{ flex: 1 }}>
                        {s.text}
                        {s.sources.map((src) => (
                          <SourceBadge key={src}>{src}</SourceBadge>
                        ))}
                        {s.chunks !== undefined && (
                          <ChunksNote>{s.chunks} chunks</ChunksNote>
                        )}
                      </span>
                    </PlanStep>
                  ))}
                </PlanList>
              </>
            )}

            {/* Generating indicator */}
            {view === "generating" && (
              <GeneratingRow>
                <AiAnvi style={{ fontSize: 14 }} />
                Generating answer…
              </GeneratingRow>
            )}

            {/* Streamed answer */}
            {answer && (
              <>
                <SubLabel>Answer</SubLabel>
                <AnswerBox>{answer}</AnswerBox>
              </>
            )}

            {/* Planview board banner */}
            {view === "done" && planviewResult && (
              <PlanviewBanner>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 700 }}>
                  <CheckmarkCircleFilled />
                  Planview board created — {planviewResult.board_name}
                </div>
                <div style={{ display: "flex", gap: 12, marginTop: 2 }}>
                  <PlanviewStat>{planviewResult.activities} activities</PlanviewStat>
                  <PlanviewStat>{planviewResult.total_cards} cards</PlanviewStat>
                  {planviewResult.board_id && (
                    <a
                      href={`https://app.projectplace.com/boards/${planviewResult.board_id}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ fontSize: 11, color: "#1565c0", textDecoration: "underline" }}
                    >
                      Open in Planview ↗
                    </a>
                  )}
                </div>
                {planviewResult.errors.length > 0 && (
                  <div style={{ fontSize: 10, color: "#c62828", marginTop: 2 }}>
                    {planviewResult.errors.length} error(s): {planviewResult.errors[0]}
                  </div>
                )}
              </PlanviewBanner>
            )}

            {/* Document success banner */}
            {view === "done" && resultDocId && (
              <SuccessBanner>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <CheckmarkCircleFilled />
                  Result saved as document
                </div>
                <SuccessLinks>
                  <DocLink
                    href={`/agent-ui/api/runs/${resultDocId}`}
                    target="_blank"
                    rel="noreferrer"
                    download
                  >
                    Download ↓
                  </DocLink>
                  <DocLink href="/search" onClick={(e) => { e.preventDefault(); window.location.href = `/search?doc=${resultDocId}`; }}>
                    Open in Search ↗
                  </DocLink>
                  <DocLink href="/documents">
                    Manage ↗
                  </DocLink>
                </SuccessLinks>
              </SuccessBanner>
            )}
          </>
        )}

        {/* ── ERROR ── */}
        {view === "error" && (
          <>
            {planSteps.length > 0 && (
              <>
                <SubLabel>Plan</SubLabel>
                <PlanList>
                  {planSteps.map((s, i) => (
                    <PlanStep key={i} $state={s.state}>
                      <StepDot $state={s.state}>
                        {s.state === "done" ? "✓" : s.state === "error" ? "✗" : "○"}
                      </StepDot>
                      <span style={{ flex: 1 }}>{s.text}</span>
                    </PlanStep>
                  ))}
                </PlanList>
              </>
            )}
            <div
              style={{
                background: "#ffebee",
                border: "1px solid #ffcdd2",
                borderRadius: 6,
                padding: "10px 12px",
                fontSize: 12,
                color: "#c62828",
              }}
            >
              <strong>Error:</strong> {errorMsg}
            </div>
          </>
        )}
      </DrawerBody>

      <DrawerFooter>
        {view === "idle" ? (
          <ButtonEmpty onClick={onClose}>Close</ButtonEmpty>
        ) : (
          <>
            <ButtonEmpty onClick={onClose}>Close</ButtonEmpty>
            {(view === "done" || view === "error") && (
              <ButtonPrimary onClick={resetRun}>Run again</ButtonPrimary>
            )}
            {(view === "running" || view === "generating") && (
              <ButtonEmpty onClick={resetRun}>Cancel</ButtonEmpty>
            )}
          </>
        )}
      </DrawerFooter>
    </Drawer>
  );
}
