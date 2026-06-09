import type { ComplianceStatus } from "@/types/compliance";
import { color } from "@planview/pv-utilities";
import { Chip } from "@planview/pv-uikit";

const COLOR_MAP: Record<ComplianceStatus, string> = {
  COMPLIANT: color.success400,
  WARNING: color.warning400,
  NON_COMPLIANT: color.error400,
  UNCHECKED: color.gray400,
  SCANNING: color.info400,
};

const LABEL_MAP: Record<ComplianceStatus, string> = {
  COMPLIANT: "Compliant",
  WARNING: "Warning",
  NON_COMPLIANT: "Non-Compliant",
  UNCHECKED: "Unchecked",
  SCANNING: "Scanning…",
};

interface Props {
  status: ComplianceStatus;
}

export function ComplianceBadge({ status }: Props) {
  return (
    <Chip
      disabled
      color={COLOR_MAP[status]}
      label={LABEL_MAP[status].toLocaleUpperCase()}
    />
  );
}
