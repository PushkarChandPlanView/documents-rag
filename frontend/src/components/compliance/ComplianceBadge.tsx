import styled from "styled-components";
import type { ComplianceStatus } from "@/types/compliance";
import { color } from "@planview/pv-utilities";

const COLOR_MAP: Record<ComplianceStatus, { bg: string; text: string }> = {
  COMPLIANT: { bg: color.success100, text: color.success400 },
  WARNING: { bg: color.warning100, text: color.warning400 },
  NON_COMPLIANT: { bg: color.error100, text: color.error400 },
  UNCHECKED: { bg: color.gray100, text: color.gray400 },
  SCANNING: { bg: color.info100, text: color.info400 },
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
  width: fit-content;
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
