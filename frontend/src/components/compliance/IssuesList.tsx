import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { Grid, GridCellBase } from "@planview/pv-grid";
import type { Column, GridRowMeta } from "@planview/pv-grid";
import { ButtonEmpty, Chip } from "@planview/pv-uikit";
import { Warning } from "@planview/pv-icons";
import { useComplianceIssues } from "@/hooks/useCompliance";
import type { ComplianceIssueFailedRule, ComplianceIssueItem, ComplianceStatus } from "@/types/compliance";

// ── Row model ─────────────────────────────────────────────────────────────────

type IssueRow = {
  id: string;
  documentId: string;
  documentName: string;
  status: ComplianceStatus;
  checkedAt: string;
  isStale: boolean;
  failingRules: ComplianceIssueFailedRule[];
  _item: ComplianceIssueItem;
};

type IssueRowMeta = GridRowMeta<IssueRow>;

// ── Styles ────────────────────────────────────────────────────────────────────
const COLOR_MAP: Record<ComplianceStatus, string> = {
  COMPLIANT: color.success100,
  WARNING: color.warning100,
  NON_COMPLIANT: color.error100,
  UNCHECKED: color.gray100,
  SCANNING: color.info100,
};

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
`;

const GridWrapper = styled.div`
  flex: 1;
  min-height: 0;
`;

const DocNameBtn = styled.button`
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  ${text.small};
  font-weight: 600;
  color: ${color.backgroundPrimary};
  text-align: left;
  &:hover {
    text-decoration: underline;
  }
`;



const LoadMore = styled.div`
  display: flex;
  justify-content: center;
  padding: ${spacing.medium}px;
  border-top: 1px solid ${color.borderLight};
  flex-shrink: 0;
`;

const Empty = styled.div`
  ${text.small};
  color: ${color.textSecondary};
  text-align: center;
  padding: ${spacing.large}px;
`;

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}

function buildGridData(items: ComplianceIssueItem[]) {
  const ids: string[] = [];
  const data = new Map<string, IssueRow>();
  const meta = new Map<string, IssueRowMeta>();

  items.forEach((item) => {
    const row: IssueRow = {
      id: item.report_id,
      documentId: item.document_id,
      documentName: item.document_name,
      status: item.status,
      checkedAt: item.checked_at,
      isStale: item.is_stale,
      failingRules: item.failing_rules,
      _item: item,
    };
    ids.push(item.report_id);
    data.set(item.report_id, row);
    meta.set(item.report_id, { type: "leaf" });
  });

  return { ids, data, meta };
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  statusFilter: ComplianceStatus | null;
}

export function IssuesList({ statusFilter }: Props) {
  const navigate = useNavigate();
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useComplianceIssues(
    statusFilter ?? undefined,
  );

  const items = useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data]);

  const gridData = useMemo(() => buildGridData(items), [items]);

  const columns = useMemo(
    (): Column<IssueRow>[] => [
      {
        id: "documentName",
        label: "Document",
        minWidth: 160,
        width: 260,
        resizable: true,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <DocNameBtn
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/documents/${row.documentId}`);
                  }}
                >
                  {row.documentName}
                </DocNameBtn>
              </GridCellBase>
            );
          },
        },
      },
      {
        id: "status",
        label: "Status",
        width: 150,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <Chip
                  label={row.status}
                  icon={row.isStale ? <Warning /> : undefined}
                  color={COLOR_MAP[row.status]}
                  disabled
                />
              </GridCellBase>
            );
          },
        },
      },
      {
        id: "checkedAt",
        label: "Checked",
        width: 150,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <span style={{ fontSize: 12, color: color.textSecondary }}>{fmtDate(row.checkedAt)}</span>
              </GridCellBase>
            );
          },
        },
      },
      {
        id: "failingRules",
        label: "Failed Rules",
        minWidth: 160,
        width: 300,
        resizable: true,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                {row.failingRules.map((r, i) => (
                  <Chip
                    disabled
                    key={i}
                    color={r.severity === "critical" ? color.error100 : color.warning100}
                    label={r.rule_name}
                    tooltip={r.detail ?? r.rule_name}
                  />
                ))}
              </GridCellBase>
            );
          },
        },
      },
    ],
    [gridData, navigate],
  );

  if (isLoading) return <Empty>Loading issues…</Empty>;
  if (!items.length) return <Empty>No compliance issues found.</Empty>;

  return (
    <Wrapper>
      <GridWrapper>
        <Grid<IssueRow, IssueRowMeta>
          label="Compliance Issues"
          columns={columns}
          rows={gridData}
          loading={isLoading}
          rowHeight="medium"
          selectionMode="none"
          onRowClick={(rowId) => {
            const row = gridData.data.get(String(rowId));
            if (row) navigate(`/documents/${row.documentId}`);
          }}
        />
      </GridWrapper>

      {hasNextPage && (
        <LoadMore>
          <ButtonEmpty onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? "Loading…" : "Load more"}
          </ButtonEmpty>
        </LoadMore>
      )}
    </Wrapper>
  );
}
