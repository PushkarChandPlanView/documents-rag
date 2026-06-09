import { useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { ButtonEmpty } from "@planview/pv-uikit";
import { EditDiffModal } from "./EditDiffModal";

const Card = styled.div`
  width: 100%;
  border-radius: 8px;
  border: 1px solid ${color.borderLight};
  background: ${color.backgroundNeutral0};
  overflow: hidden;
`;

const CardHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${spacing.small}px;
  padding: ${spacing.small}px ${spacing.medium}px;
  background: ${color.backgroundNeutral50};
  border-bottom: 1px solid ${color.borderLight};
`;

const CardTitle = styled.span`
  ${text.regularSemibold};
  color: ${color.textPrimary};
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const StatusBanner = styled.div<{ $status: "approved" | "rejected" }>`
  padding: ${spacing.small}px ${spacing.medium}px;
  ${text.small};
  color: ${({ $status }) => $status === "approved" ? color.success400 : color.error400};
  background: ${({ $status }) => $status === "approved" ? color.success0 : color.error0};
`;

interface Props {
  documentId: string;
  editId: string;
  instruction: string;
  proposedContent: string;
  initialStatus: "pending" | "approved" | "rejected";
}

export function EditProposalCard({
  documentId,
  editId,
  instruction,
  proposedContent,
  initialStatus,
}: Props) {
  const [modalOpen, setModalOpen] = useState(false);
  const [localStatus, setLocalStatus] = useState(initialStatus);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle title={instruction}>Proposed edit: {instruction}</CardTitle>
          {localStatus === "pending" && (
            <ButtonEmpty onClick={() => setModalOpen(true)}>
              Review Changes
            </ButtonEmpty>
          )}
        </CardHeader>

        {localStatus !== "pending" && (
          <StatusBanner $status={localStatus as "approved" | "rejected"}>
            {localStatus === "approved"
              ? "✓ Approved — document is being reprocessed."
              : "✗ Rejected — no changes were applied."}
          </StatusBanner>
        )}
      </Card>

      {modalOpen && (
        <EditDiffModal
          documentId={documentId}
          editId={editId}
          instruction={instruction}
          proposedContent={proposedContent}
          initialStatus={localStatus}
          onClose={() => setModalOpen(false)}
          onStatusChange={(status) => setLocalStatus(status)}
        />
      )}
    </>
  );
}
