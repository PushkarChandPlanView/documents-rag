import { useState } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { Toolbar, ToolbarSectionLeft, ToolbarSectionRight, ToolbarButtonEmpty } from "@planview/pv-toolbar";
import { Help } from "@planview/pv-icons";
import Layout from "@/components/layout/Layout";
import { DashboardStats } from "@/components/compliance/DashboardStats";
import { IssuesList } from "@/components/compliance/IssuesList";
import { useComplianceStats } from "@/hooks/useCompliance";
import { useDocuments } from "@/hooks/useDocuments";
import type { ComplianceStatus } from "@/types/compliance";

// ── Styles ────────────────────────────────────────────────────────────────────

const PageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: hidden;
`;

const Body = styled.div`
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  padding: ${spacing.large}px;
  display: flex;
  flex-direction: column;
  gap: ${spacing.large}px;
`;

const Section = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
`;

const SectionTitle = styled.h2`
  margin: 0;
  ${text.regularSemibold}
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: ${color.textSecondary};
`;

const DocStatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: ${spacing.medium}px;
`;

const DocCard = styled.div<{ $color: string }>`
  padding: ${spacing.medium}px;
  border-radius: 8px;
  background: ${({ $color }) => $color}18;
  border: 1px solid ${({ $color }) => $color}30;
  &:hover {
    border-color: ${({ $color }) => $color};
  }
`;

const DocCount = styled.div<{ $color: string }>`
  ${text.h1}
  font-size: large;
  color: ${({ $color }) => $color};
  line-height: 1;
  font-size: 28px;
  font-weight: 700;
`;

const DocLabel = styled.div`
  ${text.small};
  font-weight: 500;
  margin-top: 4px;
  color: ${color.textSecondary};
`;

const IssuesContainer = styled.div`
  flex: 1 1 0;
  min-height: 300px;
  border: 1px solid ${color.borderLight};
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
`;

const ToolbarTitle = styled.span`
  ${text.small};
  font-weight: 700;
`;

// ── Document stat cards ───────────────────────────────────────────────────────

const DOC_CARDS = [
  { key: "total", label: "Total Documents", color: "#1565c0" },
  { key: "completed", label: "Completed", color: "#2e7d32" },
  { key: "processing", label: "Processing", color: "#6a1a9a" },
  { key: "failed", label: "Failed", color: "#c62828" },
] as const;

function useDocumentStats() {
  const { data } = useDocuments(undefined, 500);
  const items = data?.pages.flatMap((p) => p.items) ?? [];
  const docs = items.filter((i) => i.type === "document");
  return {
    total: docs.length,
    completed: docs.filter((d) => d.status === "COMPLETED").length,
    processing: docs.filter((d) => d.status === "PROCESSING").length,
    failed: docs.filter((d) => d.status === "FAILED").length,
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Overview() {
  const navigate = useNavigate();
  const docStats = useDocumentStats();
  const { data: complianceStats } = useComplianceStats();
  const [statusFilter, setStatusFilter] = useState<ComplianceStatus | null>(null);

  const docStatValues: Record<string, number> = {
    total: docStats.total,
    completed: docStats.completed,
    processing: docStats.processing,
    failed: docStats.failed,
  };

  return (
    <Layout>
      <PageWrapper>
        <Toolbar label="Overview toolbar">
          <ToolbarSectionLeft>
            <ToolbarTitle>Overview</ToolbarTitle>
          </ToolbarSectionLeft>
          <ToolbarSectionRight moreMenuLabel="More actions">
            <ToolbarButtonEmpty icon={<Help />} tooltip="Help" />
          </ToolbarSectionRight>
        </Toolbar>

        <Body>
          {/* Document Health */}
          <Section>
            <SectionTitle>Document Health</SectionTitle>
            <DocStatsGrid>
              {DOC_CARDS.map(({ key, label, color: cardColor }) => (
                <DocCard
                  key={key}
                  $color={cardColor}
                  style={{ cursor: key !== "total" ? "pointer" : "default" }}
                  onClick={() => key !== "total" && navigate("/documents")}
                >
                  <DocCount $color={cardColor}>{docStatValues[key]}</DocCount>
                  <DocLabel>{label}</DocLabel>
                </DocCard>
              ))}
            </DocStatsGrid>
          </Section>

          {/* Compliance Health */}
          <Section>
            <SectionTitle>Compliance Health</SectionTitle>
            {complianceStats && (
              <DashboardStats stats={complianceStats} activeFilter={statusFilter} onFilter={setStatusFilter} />
            )}
          </Section>

          {/* Compliance Issues */}
          <Section style={{ flex: "1 1 0", minHeight: 0 }}>
            <SectionTitle>
              {statusFilter ? `${statusFilter.replace("_", " ")} Issues` : "Recent Compliance Issues"}
            </SectionTitle>
            <IssuesContainer>
              <IssuesList statusFilter={statusFilter} />
            </IssuesContainer>
          </Section>
        </Body>
      </PageWrapper>
    </Layout>
  );
}
