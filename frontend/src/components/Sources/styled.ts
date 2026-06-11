import { borderRadius, color, spacing, text } from "@planview/pv-utilities";
import styled from "styled-components";

// ── Modal shell ───────────────────────────────────────────────────────────────
export const Container = styled.div`
  width: 650px;
  min-height: 380px;
  display: flex;
  flex-direction: column;
`;

export const FooterRow = styled.div`
  display: flex;
  gap: ${spacing.small}px;
  justify-content: space-between;
  align-items: center;
  padding: ${spacing.small}px;
`;

export const RightSection = styled.div`
  display: flex;
  gap: ${spacing.small}px;
`;

// ── Form ──────────────────────────────────────────────────────────────────────
export const FormGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: ${spacing.small}px;
  padding: ${spacing.medium}px;
  overflow-y: auto;
`;

export const FullWidth = styled.div`
  grid-column: 1 / -1;
`;

export const FormHeader = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.medium}px;
  padding: ${spacing.medium}px ${spacing.medium}px ${spacing.small}px;
`;

export const FormHeaderIconBox = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #e8f4fd;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  svg { width: 20px; height: 20px; color: ${color.blue400}; }
`;

export const FormHeaderText = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

export const FormHeaderTitle = styled.div`
  font-size: 15px;
  font-weight: 600;
  color: ${color.textPrimary};
`;

export const FormHeaderSub = styled.div`
  ${text.small};
  color: ${color.textSecondary};
`;

// ── Queue ─────────────────────────────────────────────────────────────────────
export const QueueHeaderRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: ${spacing.medium}px ${spacing.medium}px ${spacing.small}px;
`;

export const QueueHeaderTitle = styled.div`
  font-size: 15px;
  font-weight: 700;
  color: ${color.textPrimary};
`;

export const QueueHeaderCount = styled.div`
  ${text.small};
  color: ${color.textSecondary};
`;

export const QueueList = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${spacing.small}px ${spacing.medium}px 0;
`;

export const QueueItemRow = styled.div`
  display: flex;
  align-items: center;
  border: 1px solid ${color.gray200};
  border-radius: 6px;
  margin-bottom: ${spacing.small}px;
  padding: ${spacing.xsmall}px ${spacing.small}px;
  gap: ${spacing.small}px;
`;

export const QueueItemIconBox = styled.div`
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #e8f4fd;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  svg { width: 16px; height: 16px; color: ${color.blue400}; }
`;

export const QueueItemText = styled.div`
  flex: 1;
  min-width: 0;
`;

export const QueueItemLabel = styled.div`
  ${text.small};
  font-weight: 600;
  color: ${color.textPrimary};
`;

export const QueueItemSub = styled.div`
  ${text.small};
  color: ${color.textSecondary};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export const InfoSection = styled.div`
  padding: ${spacing.small}px ${spacing.medium}px 0;
`;

export const InfoBanner = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.small}px;
  padding: ${spacing.xsmall}px;
  background: ${color.blue100};
  ${borderRadius.medium}
  ${text.regular};
  color: ${color.textSecondary};
`;

export const EmptyState = styled.div`
  ${text.small};
  color: ${color.textSecondary};
  display: flex;
  align-items: center;
  justify-content: center;
  padding: ${spacing.xlarge}px;
`;
