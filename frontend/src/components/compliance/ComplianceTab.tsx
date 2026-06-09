import styled from "styled-components";
import { align, color, spacing, text } from "@planview/pv-utilities";
import { ButtonEmpty, Chip, Divider } from "@planview/pv-uikit";
import { CheckmarkCircleFilled, CrossCircleFilled, InfoFilled, Refresh, WarningFilled } from "@planview/pv-icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ComplianceBadge } from "./ComplianceBadge";
import { useComplianceReport, useTriggerScan } from "@/hooks/useCompliance";
import type { ComplianceRuleResult, Location } from "@/types/compliance";

// ── Styles ────────────────────────────────────────────────────────────────────

const Container = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.medium}px;
  padding: ${spacing.medium}px;
  overflow-y: auto;
  height: 100%;
`;

const Header = styled.div`
  ${align.centerH}
  justify-content: space-between;
`;

const StatusRow = styled.div`
  display: flex;
  gap: ${spacing.xsmall}px;
  flex-direction: column;
  align-self: center;
  align-items: flex-start;
`;

const CheckedAt = styled.span`
  ${text.regular};
  color: ${color.textSecondary};
`;

const Banner = styled.div<{ $variant: "warning" | "info" }>`
  display: flex;
  align-items: flex-start;
  gap: ${spacing.small}px;
  padding: ${spacing.small}px ${spacing.medium}px;
  border-radius: 6px;
  ${text.regular};
  background: ${({ $variant }) => ($variant === "warning" ? color.warning100 : color.info100)};
  color: ${({ $variant }) => ($variant === "warning" ? color.warning600 : color.info600)};

  svg {
    flex-shrink: 0;
    margin-top: 1px;
  }
`;

const BannerText = styled.span`
  flex: 1;
`;

const InsightsCard = styled.div`
  padding: ${spacing.medium}px;
  border-radius: 6px;
  background: ${color.warning0};
  border: 1px solid ${color.warning100};
  display: flex;
  flex-direction: column;
  gap: ${spacing.xsmall}px;
`;

const InsightsTitle = styled.div`
  ${text.regular};
  font-weight: 700;
  color: ${color.warning400};
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
`;

const InsightsMarkdown = styled.div`
  ${text.regular};
  color: ${color.textPrimary};
  line-height: 1.5;

  p {
    margin: 0 0 ${spacing.xsmall}px;
  }
  p:last-child {
    margin-bottom: 0;
  }
  ul,
  ol {
    margin: 0 0 ${spacing.xsmall}px;
    padding-left: ${spacing.medium}px;
  }
  li {
    margin-bottom: 2px;
  }
  strong {
    font-weight: 600;
  }
  code {
    font-family: monospace;
    font-size: 0.9em;
  }
`;

const SectionLabel = styled.div`
  ${text.regular};
  font-weight: 600;
  color: ${color.textSecondary};
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const RuleList = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
`;

const RuleRow = styled.div<{ $passed: boolean }>`
  padding: ${spacing.small}px ${spacing.medium}px;
  border-radius: 6px;
  border: 1px solid ${({ $passed }) => ($passed ? color.success100 : color.error100)};
  background: ${({ $passed }) => ($passed ? color.success0 : color.error0)};
`;

const RuleHeader = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.small}px;
  flex-wrap: wrap;
`;

const RuleName = styled.span`
  ${text.regular};
  font-weight: 600;
  color: ${color.textPrimary};
  flex: 1;
`;

const RuleDetail = styled.div`
  ${text.regular};
  color: ${color.textSecondary};
  margin-top: 4px;
`;

const LocationChips = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: ${spacing.xsmall}px;
`;

const ExcerptBlock = styled.blockquote`
  margin: 4px 0 0;
  padding: 4px 8px;
  border-left: 3px solid ${color.borderInfo};
  font-style: italic;
  ${text.regular};
  color: ${color.textSecondary};
`;

const EmptyState = styled.div`
  ${text.regular};
  color: ${color.textSecondary};
  text-align: center;
  padding: ${spacing.large}px;
`;

const SEVERITY_COLORS: Record<string, string> = {
  critical: color.error400,
  warning: color.warning400,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function LocationDisplay({ loc, ruleType }: { loc: Location; ruleType: string }) {
  if (ruleType === "llm_check") {
    return <ExcerptBlock>"{loc.excerpt}"</ExcerptBlock>;
  }
  const label = [
    loc.page_number != null && `Page ${loc.page_number}`,
    loc.chunk_index != null && `Chunk ${loc.chunk_index}`,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <div>
      {label && <Chip label={label} color={color.iconInfo} disabled tooltip={loc.excerpt || undefined} />}
      {loc.excerpt && <ExcerptBlock>…{loc.excerpt}…</ExcerptBlock>}
    </div>
  );
}

function RuleResultRow({ result }: { result: ComplianceRuleResult }) {
  const visibleLocations = result.locations?.filter((l) => l.excerpt) ?? [];
  return (
    <RuleRow $passed={result.passed}>
      <RuleHeader>
        {result.passed ? (
          <CheckmarkCircleFilled color={color.success400} />
        ) : (
          <CrossCircleFilled color={color.error400} />
        )}
        <RuleName>{result.rule_name}</RuleName>
        <Chip label={result.severity.toLocaleUpperCase()} color={SEVERITY_COLORS[result.severity]} disabled />
      </RuleHeader>
      {result.detail && <RuleDetail>{result.detail}</RuleDetail>}
      {!result.passed && visibleLocations.length > 0 && (
        <LocationChips>
          {visibleLocations.slice(0, 5).map((loc, i) => (
            <LocationDisplay key={i} loc={loc} ruleType={result.rule_type} />
          ))}
          {visibleLocations.length > 5 && <Chip label={`+${visibleLocations.length - 5} more`} disabled />}
        </LocationChips>
      )}
    </RuleRow>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  documentId: string;
}

export function ComplianceTab({ documentId }: Props) {
  const isScanning = (status?: string) => status === "SCANNING";

  const {
    data: report,
    isLoading,
    isError,
  } = useComplianceReport(documentId, {
    refetchInterval: (query) => (isScanning(query.state.data?.status) ? 5000 : false),
  });

  const { mutate: triggerScan, isPending: submitting } = useTriggerScan(documentId);
  const scanning = isScanning(report?.status) || submitting;

  const fmtDate = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

  if (isLoading) return <EmptyState>Loading compliance report…</EmptyState>;
  if (isError) return <EmptyState>Could not load compliance report.</EmptyState>;

  const ScanButton = (
    <ButtonEmpty icon={<Refresh />} onClick={() => !scanning && triggerScan()} disabled={scanning}>
      {submitting || isScanning(report?.status)
        ? "In Progress…"
        : report?.status === "UNCHECKED"
          ? "Scan Now"
          : "Re-scan"}
    </ButtonEmpty>
  );

  // UNCHECKED
  if (!report || report.status === "UNCHECKED") {
    return (
      <Container>
        <Header>
          <StatusRow>
            <ComplianceBadge status="UNCHECKED" />
            <CheckedAt>Not scanned yet.</CheckedAt>
          </StatusRow>
          {ScanButton}
        </Header>
        <EmptyState>Run a compliance scan to check this document against all active rules.</EmptyState>
      </Container>
    );
  }

  // SCANNING
  if (report.status === "SCANNING") {
    return (
      <Container>
        <Header>
          <StatusRow>
            <ComplianceBadge status="SCANNING" />
            <CheckedAt>Scan started {fmtDate(report.checked_at)}</CheckedAt>
          </StatusRow>
          {ScanButton}
        </Header>
        <Banner $variant="info">
          <BannerText>
            Scan in progress — checking all compliance rules. This page will update automatically.
          </BannerText>
        </Banner>
      </Container>
    );
  }

  const failed = report.results.filter((r) => !r.passed);
  const passed = report.results.filter((r) => r.passed);

  return (
    <Container>
      <Header>
        <StatusRow>
          <ComplianceBadge status={report.status} />
          <CheckedAt>Checked {fmtDate(report.checked_at)}</CheckedAt>
        </StatusRow>
        {ScanButton}
      </Header>

      {report.is_stale && (
        <Banner $variant="warning">
          <WarningFilled color={color.warning400} />
          <BannerText>Rules updated since last scan — results may be outdated. Run a new scan to refresh.</BannerText>
        </Banner>
      )}

      {report.insights && (
        <InsightsCard>
          <InsightsTitle>
            <InfoFilled color={color.error400} />
            Recommendations
          </InsightsTitle>
          <InsightsMarkdown>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.insights}</ReactMarkdown>
          </InsightsMarkdown>
        </InsightsCard>
      )}

      {failed.length > 0 && (
        <>
          <SectionLabel>Failed Rules ({failed.length})</SectionLabel>
          <RuleList>
            {failed.map((r) => (
              <RuleResultRow key={r.id} result={r} />
            ))}
          </RuleList>
        </>
      )}

      {passed.length > 0 && failed.length > 0 && <Divider />}

      {passed.length > 0 && (
        <>
          <SectionLabel>Passed Rules ({passed.length})</SectionLabel>
          <RuleList>
            {passed.map((r) => (
              <RuleResultRow key={r.id} result={r} />
            ))}
          </RuleList>
        </>
      )}
    </Container>
  );
}
