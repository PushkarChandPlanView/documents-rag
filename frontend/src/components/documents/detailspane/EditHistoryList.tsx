import { useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { ButtonEmpty, Chip } from "@planview/pv-uikit";
import { useDocumentEdits } from "@/hooks/useEdits";
import type { DocumentEdit } from "@/api/edits";
import { EditDiffModal } from "@/components/chat/EditDiffModal";

const Container = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
  padding: ${spacing.medium}px;
  overflow-y: auto;
  height: 100%;
`;

const EmptyState = styled.div`
  ${text.regular};
  color: ${color.textSecondary};
  text-align: center;
  padding: ${spacing.large}px;
`;

const EditRow = styled.div`
  padding: ${spacing.small}px ${spacing.medium}px;
  border-radius: 6px;
  border: 1px solid ${color.borderLight};
  background: ${color.backgroundNeutral0};
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${spacing.small}px;
`;

const EditInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
`;

const VersionRow = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.xsmall}px;
`;

const Instruction = styled.span`
  ${text.regular};
  color: ${color.textPrimary};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const Timestamp = styled.span`
  ${text.small};
  color: ${color.textSecondary};
`;

interface Props {
  documentId: string;
}

export function EditHistoryList({ documentId }: Props) {
  const { data, isLoading } = useDocumentEdits(documentId);
  const [previewing, setPreviewing] = useState<DocumentEdit | null>(null);

  if (isLoading) return <EmptyState>Loading history…</EmptyState>;

  const visible = data?.edits.filter((e) => e.status !== "rejected") ?? [];
  if (!visible.length)
    return <EmptyState>No approved edits yet. Request a change from the Chat tab.</EmptyState>;

  return (
    <>
      <Container>
        {visible.map((edit) => (
          <EditRow key={edit.id}>
            <EditInfo>
              <VersionRow>
                {edit.version != null && (
                  <Chip label={`v${edit.version}`} color={color.info400} disabled />
                )}
                <Instruction title={edit.instruction}>{edit.instruction}</Instruction>
              </VersionRow>
              <Timestamp>{new Date(edit.created_at).toLocaleString()}</Timestamp>
            </EditInfo>
            <ButtonEmpty onClick={() => setPreviewing(edit)}>Preview</ButtonEmpty>
          </EditRow>
        ))}
      </Container>

      {previewing && (
        <EditDiffModal
          documentId={documentId}
          editId={previewing.id}
          instruction={previewing.instruction}
          proposedContent={previewing.proposed_content}
          initialStatus={previewing.status}
          onClose={() => setPreviewing(null)}
          onStatusChange={() => {}}
        />
      )}
    </>
  );
}
