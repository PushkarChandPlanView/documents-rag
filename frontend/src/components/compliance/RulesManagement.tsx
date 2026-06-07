import { Dispatch, SetStateAction, useMemo, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { Grid, GridCellBase } from "@planview/pv-grid";
import type { Column, GridRowMeta } from "@planview/pv-grid";
import { Checkbox, Chip, DESTRUCTIVE, ListItem, Modal } from "@planview/pv-uikit";
import { Edit, Trash } from "@planview/pv-icons";
import { useComplianceRules, useDeleteRule } from "@/hooks/useCompliance";
import { RuleFormDialog } from "./RuleFormDialog";
import type { ComplianceRule } from "@/types/compliance";

// ── Row model ─────────────────────────────────────────────────────────────────

type RuleRow = {
  id: string;
  name: string;
  description: string | null;
  ruleType: string;
  severity: string;
  active: boolean;
  changed: boolean;
  _rule: ComplianceRule;
};

type RuleRowMeta = GridRowMeta<RuleRow>;

// ── Styles ────────────────────────────────────────────────────────────────────

const Container = styled.div`
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

const SEVERITY_COLORS: Record<string, string> = {
  critical: color.error100,
  warning: color.warning100,
};

const NameCell = styled.div<{ $dimmed: boolean }>`
  opacity: ${({ $dimmed }) => ($dimmed ? 0.5 : 1)};
`;

const RuleName = styled.div`
  ${text.small};
  font-weight: 600;
  color: ${color.textPrimary};
  display: flex;
  align-items: center;
  gap: 6px;
`;

const ChangedDot = styled.span`
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #e65100;
  flex-shrink: 0;
`;

const Empty = styled.div`
  ${text.small};
  color: ${color.textSecondary};
  text-align: center;
  padding: ${spacing.large}px;
`;

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  isAdmin: boolean;
  pending: Record<string, boolean>;
  setPending: Dispatch<SetStateAction<Record<string, boolean>>>;
  showCreate: boolean;
  onCloseCreate: () => void;
}

export function RulesManagement({ isAdmin, pending, setPending, showCreate, onCloseCreate }: Props) {
  const { data: rules = [], isLoading } = useComplianceRules();
  const { mutate: deleteRule } = useDeleteRule();
  const [editRule, setEditRule] = useState<ComplianceRule | null>(null);

  // Build grid rows — reflects pending toggles immediately
  const gridData = useMemo(() => {
    const ids: string[] = [];
    const data = new Map<string, RuleRow>();
    const meta = new Map<string, RuleRowMeta>();

    rules.forEach((rule) => {
      const active = pending[rule.id] !== undefined ? pending[rule.id] : rule.is_active;
      const row: RuleRow = {
        id: rule.id,
        name: rule.name,
        description: rule.description,
        ruleType: rule.rule_type.replace(/_/g, " "),
        severity: rule.severity,
        active,
        changed: pending[rule.id] !== undefined,
        _rule: rule,
      };
      ids.push(rule.id);
      data.set(rule.id, row);
      meta.set(rule.id, { type: "leaf" });
    });

    return { ids, data, meta };
  }, [rules, pending]);

  const columns = useMemo((): Column<RuleRow>[] => {
    const cols: Column<RuleRow>[] = [
      {
        id: "active",
        label: "Active",
        width: 70,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <Checkbox
                  selected={row.active}
                  disabled={!isAdmin}
                  aria-label={`Toggle rule ${row.name}`}
                  onChange={(value, event) => {
                    event.stopPropagation();
                    if (!isAdmin) return;
                    const original = row._rule.is_active;
                    setPending((prev) => {
                      if (value === original) {
                        const { [row.id]: _, ...rest } = prev;
                        return rest;
                      }
                      return { ...prev, [row.id]: value };
                    });
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
              </GridCellBase>
            );
          },
        },
      },
      {
        id: "name",
        label: "Name",
        minWidth: 160,
        width: 220,
        resizable: true,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <NameCell $dimmed={!row.active}>
                  {row.name}
                  {row.changed && <ChangedDot title="Unsaved change" />}
                </NameCell>
              </GridCellBase>
            );
          },
        },
      },
      {
        id: "description",
        label: "Description",
        minWidth: 150,
        width: 280,
        resizable: true,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <span style={{ opacity: row.active ? 1 : 0.5, fontSize: 12 }}>{row.description ?? "—"}</span>
              </GridCellBase>
            );
          },
        },
      },
      {
        id: "ruleType",
        label: "Type",
        width: 140,
      },
      {
        id: "severity",
        label: "Severity",
        width: 110,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <Chip label={row.severity.toUpperCase()} color={SEVERITY_COLORS[row.severity]} disabled />
              </GridCellBase>
            );
          },
        },
      },
    ];

    return cols;
  }, [gridData, isAdmin, setPending]);

  const [ruleToDelete, setRuleToDelete] = useState<RuleRow | null>(null);

  if (isLoading) return <Empty>Loading rules…</Empty>;
  if (rules.length === 0) return <Empty>No compliance rules defined yet.</Empty>;

  return (
    <Container>
      <GridWrapper>
        <Grid<RuleRow, RuleRowMeta>
          label="Compliance Rules"
          columns={columns}
          rows={gridData}
          loading={isLoading}
          rowHeight="medium"
          selectionMode="none"
          actionsMenu={
            isAdmin
              ? ({ row }) => (
                  <>
                    <ListItem icon={<Edit />} label="Edit" onActivate={() => setEditRule(row._rule)} />
                    <ListItem icon={<Trash />} label="Delete" onActivate={() => setRuleToDelete(row)} />
                  </>
                )
              : undefined
          }
        />
      </GridWrapper>

      {ruleToDelete && (
        <Modal
          type={DESTRUCTIVE}
          headerText="Delete Rule"
          confirmText="Delete"
          cancelText="Cancel"
          onConfirm={() => {
            deleteRule(ruleToDelete.id);
            setRuleToDelete(null);
          }}
          onCancel={() => setRuleToDelete(null)}
        >
          <p>
            Delete rule <strong>"{ruleToDelete.name}"</strong>? This cannot be undone and existing compliance reports
            referencing this rule will lose the rule association.
          </p>
        </Modal>
      )}

      {showCreate && <RuleFormDialog onClose={onCloseCreate} />}
      {editRule && <RuleFormDialog rule={editRule} onClose={() => setEditRule(null)} />}
    </Container>
  );
}
