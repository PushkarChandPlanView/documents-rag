import styled from "styled-components";
import { spacing, text } from "@planview/pv-utilities";
import type { ComplianceStats, ComplianceStatus } from "@/types/compliance";

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: ${spacing.medium}px;
`;

const Card = styled.button<{ $active: boolean; $color: string }>`
  padding: ${spacing.medium}px;
  border-radius: 8px;
  border: 2px solid ${({ $active, $color }) => ($active ? $color : "transparent")};
  background: ${({ $color }) => $color}18;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s;

  &:hover {
    border-color: ${({ $color }) => $color};
  }
`;

const Count = styled.div<{ $color: string }>`
  font-size: 28px;
  font-weight: 700;
  color: ${({ $color }) => $color};
  line-height: 1;
`;

const Label = styled.div`
  ${text.small};
  font-weight: 500;
  margin-top: 4px;
  opacity: 0.75;
  color: inherit;
`;

const CARDS: Array<{
  key: keyof ComplianceStats;
  label: string;
  color: string;
  filter?: ComplianceStatus;
}> = [
  { key: "compliant",     label: "Compliant",     color: "#2e7d32", filter: "COMPLIANT" },
  { key: "warning",       label: "Warning",       color: "#bf360c", filter: "WARNING" },
  { key: "non_compliant", label: "Non-Compliant", color: "#b71c1c", filter: "NON_COMPLIANT" },
  { key: "unchecked",     label: "Unchecked",     color: "#757575" },
];

interface Props {
  stats: ComplianceStats;
  activeFilter: ComplianceStatus | null;
  onFilter: (status: ComplianceStatus | null) => void;
}

export function DashboardStats({ stats, activeFilter, onFilter }: Props) {
  return (
    <Grid>
      {CARDS.map(({ key, label, color, filter }) => (
        <Card
          key={key}
          $color={color}
          $active={activeFilter === (filter ?? null)}
          onClick={() => onFilter(activeFilter === filter ? null : (filter ?? null))}
          type="button"
        >
          <Count $color={color}>{stats[key]}</Count>
          <Label>{label}</Label>
        </Card>
      ))}
    </Grid>
  );
}
