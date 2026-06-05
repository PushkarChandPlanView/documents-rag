import { Link } from "react-router-dom";
import styled, { keyframes } from "styled-components";
import Layout from "@/components/layout/Layout";
import { useDocuments } from "@/hooks/useDocuments";
import type { Document, ProcessingJob } from "@/types";

// ── Styled components ─────────────────────────────────────────────────────────

const PageTitle = styled.h1`
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  font-weight: 700;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
`;

const StatCardWrapper = styled.div<{ $color: string }>`
  background: #fff;
  border-radius: 8px;
  padding: 1.25rem 1.5rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  border-left: 4px solid ${({ $color }) => $color};
`;

const StatLabel = styled.p`
  margin: 0 0 0.25rem;
  color: #666;
  font-size: 0.8rem;
`;

const StatValue = styled.p`
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: #333;
`;

const SectionTitle = styled.h2`
  margin: 0 0 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: #444;
`;

const ProcessingSection = styled.div`
  margin-bottom: 2rem;
`;

const ProcessingCard = styled.div`
  background: #fff;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  margin-bottom: 0.75rem;
  border-left: 4px solid #f57c00;
`;

const DocFilename = styled.p`
  margin: 0 0 0.75rem;
  font-weight: 600;
  font-size: 0.9rem;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const ProgressHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
`;

const ProgressPct = styled.span`
  font-size: 0.75rem;
  font-weight: 600;
  color: #f57c00;
`;

const ActiveStageLabel = styled.span`
  font-size: 0.75rem;
  color: #666;
`;

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.45; }
`;

const ProgressTrack = styled.div`
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.75rem;
`;

const ProgressFill = styled.div<{ $pct: number; $active: boolean }>`
  height: 100%;
  width: ${({ $pct }) => $pct}%;
  background: #f57c00;
  border-radius: 3px;
  transition: width 0.5s ease;
  animation: ${({ $active }) => ($active ? pulse : "none")} 1.4s ease-in-out infinite;
`;

const StagesRow = styled.div`
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
`;

const StagePill = styled.span<{ $status: string }>`
  font-size: 0.68rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: ${({ $status }) => STATUS_BG[$status] ?? "#f0f0f0"};
  color: ${({ $status }) => STATUS_FG[$status] ?? "#555"};
`;

const QuickLinksGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
`;

const QuickLinkAnchor = styled(Link)`
  text-decoration: none;
`;

const QuickLinkCard = styled.div<{ $color: string }>`
  background: #fff;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: box-shadow 0.2s;
  border-top: 3px solid ${({ $color }) => $color};
`;

const QuickLinkTitle = styled.h3<{ $color: string }>`
  margin: 0 0 0.5rem;
  color: ${({ $color }) => $color};
  font-size: 1rem;
`;

const QuickLinkDesc = styled.p`
  margin: 0;
  color: #666;
  font-size: 0.875rem;
`;

// ── Constants ─────────────────────────────────────────────────────────────────

const STAGE_ORDER = ["TEXT_EXTRACTION", "CHUNKING", "EMBEDDING", "SUMMARIZATION"] as const;

const STAGE_LABELS: Record<string, string> = {
  TEXT_EXTRACTION: "Extract",
  CHUNKING: "Chunk",
  EMBEDDING: "Embed",
  SUMMARIZATION: "Summarize",
};

const STATUS_BG: Record<string, string> = {
  COMPLETED:   "#e8f5e9",
  IN_PROGRESS: "#fff3e0",
  FAILED:      "#ffebee",
  PENDING:     "#f5f5f5",
};

const STATUS_FG: Record<string, string> = {
  COMPLETED:   "#2e7d32",
  IN_PROGRESS: "#e65100",
  FAILED:      "#c62828",
  PENDING:     "#757575",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function jobMap(jobs: ProcessingJob[]): Record<string, ProcessingJob> {
  return Object.fromEntries(jobs.map((j) => [j.stage, j]));
}

function calcProgress(jobs: ProcessingJob[]): number {
  const completed = jobs.filter((j) => j.status === "COMPLETED").length;
  return Math.round((completed / STAGE_ORDER.length) * 100);
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <StatCardWrapper $color={color}>
      <StatLabel>{label}</StatLabel>
      <StatValue>{value}</StatValue>
    </StatCardWrapper>
  );
}

function DocProcessingCard({ doc }: { doc: Document }) {
  const jobs = jobMap(doc.processing_jobs);
  const pct = calcProgress(doc.processing_jobs);
  const activeStage = doc.processing_jobs.find((j) => j.status === "IN_PROGRESS");

  return (
    <ProcessingCard>
      <DocFilename title={doc.filename}>{doc.filename}</DocFilename>
      <ProgressHeader>
        <ActiveStageLabel>
          {activeStage ? STAGE_LABELS[activeStage.stage] ?? activeStage.stage : doc.status === "PENDING" ? "Queued" : "Processing"}
        </ActiveStageLabel>
        <ProgressPct>{pct}%</ProgressPct>
      </ProgressHeader>
      <ProgressTrack>
        <ProgressFill $pct={pct} $active={!!activeStage} />
      </ProgressTrack>
      <StagesRow>
        {STAGE_ORDER.map((stage) => {
          const job = jobs[stage];
          const status = job?.status ?? "PENDING";
          return (
            <StagePill key={stage} $status={status}>
              {STAGE_LABELS[stage]}
            </StagePill>
          );
        })}
      </StagesRow>
    </ProcessingCard>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { data } = useDocuments();
  const docs = data?.items ?? [];
  const completed  = docs.filter((d) => d.status === "COMPLETED").length;
  const processing = docs.filter((d) => d.status === "PROCESSING" || d.status === "PENDING");

  return (
    <Layout>
      <PageTitle>Dashboard</PageTitle>

      <StatsGrid>
        <StatCard label="Total Documents"  value={docs.length}       color="#1a73e8" />
        <StatCard label="Ready for Q&A"    value={completed}          color="#2e7d32" />
        <StatCard label="Processing"       value={processing.length}  color="#f57c00" />
      </StatsGrid>

      {processing.length > 0 && (
        <ProcessingSection>
          <SectionTitle>Processing</SectionTitle>
          {processing.map((doc) => (
            <DocProcessingCard key={doc.id} doc={doc} />
          ))}
        </ProcessingSection>
      )}

      <QuickLinksGrid>
        {[
          { title: "Upload Documents", desc: "Add PDF, DOCX, or TXT files for analysis", path: "/documents", color: "#1a73e8" },
          { title: "Semantic Search",  desc: "Find relevant content across all your documents", path: "/search", color: "#7b1fa2" },
          { title: "Ask Questions",    desc: "Chat with your documents using local AI", path: "/chat", color: "#00796b" },
        ].map((card) => (
          <QuickLinkAnchor key={card.path} to={card.path}>
            <QuickLinkCard $color={card.color}>
              <QuickLinkTitle $color={card.color}>{card.title}</QuickLinkTitle>
              <QuickLinkDesc>{card.desc}</QuickLinkDesc>
            </QuickLinkCard>
          </QuickLinkAnchor>
        ))}
      </QuickLinksGrid>
    </Layout>
  );
}
