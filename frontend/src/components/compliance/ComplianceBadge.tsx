import styled from "styled-components";
import type { ComplianceStatus } from "@/types/compliance";

const COLOR_MAP: Record<ComplianceStatus, { bg: string; text: string }> = {
  COMPLIANT: { bg: "#e8f5e9", text: "#2e7d32" },
  WARNING:   { bg: "#ffdcb9", text: "#bf360c" },
  NON_COMPLIANT: { bg: "#fccfcf", text: "#b71c1c" },
  UNCHECKED: { bg: "#f5f5f5", text: "#757575" },
  SCANNING:  { bg: "#e3f2fd", text: "#1565c0" },
};

const LABEL_MAP: Record<ComplianceStatus, string> = {
  COMPLIANT: "Compliant",
  WARNING: "Warning",
  NON_COMPLIANT: "Non-Compliant",
  UNCHECKED: "Unchecked",
  SCANNING: "Scanning…",
};

const Badge = styled.span<{ $status: ComplianceStatus }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  background: ${({ $status }) => COLOR_MAP[$status].bg};
  color: ${({ $status }) => COLOR_MAP[$status].text};
`;

const Dot = styled.span<{ $status: ComplianceStatus }>`
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: ${({ $status }) => COLOR_MAP[$status].text};
`;

interface Props {
  status: ComplianceStatus;
}

export function ComplianceBadge({ status }: Props) {
  return (
    <Badge $status={status}>
      <Dot $status={status} />
      {LABEL_MAP[status]}
    </Badge>
  );
}
