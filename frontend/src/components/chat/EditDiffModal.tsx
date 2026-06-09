import { useState } from "react";
import styled from "styled-components";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { color, spacing, text } from "@planview/pv-utilities";
import { ButtonDestructive, ButtonEmpty, ButtonPrimary, Modal, MODAL_LARGE } from "@planview/pv-uikit";
import { CheckmarkCircleFilled, CrossCircleFilled } from "@planview/pv-icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { editsApi } from "@/api/edits";

// ── Styles ────────────────────────────────────────────────────────────────────

const ModalBody = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.small}px;
  height: 60vh;
  min-height: 0;
`;

const Instruction = styled.p`
  ${text.regular};
  color: ${color.textSecondary};
  margin: 0;
  flex-shrink: 0;
`;

const ContentPanel = styled.div`
  flex: 1;
  overflow: auto;
  border: 1px solid ${color.borderLight};
  border-radius: 6px;
  padding: ${spacing.medium}px;
  background: ${color.backgroundNeutral0};
`;

const MarkdownContent = styled.div`
  ${text.regular};
  color: ${color.textPrimary};
  line-height: 1.6;

  p { margin: 0 0 ${spacing.xsmall}px; }
  p:last-child { margin-bottom: 0; }
  h1, h2, h3 { margin: ${spacing.small}px 0 ${spacing.xsmall}px; font-weight: 600; }
  ul, ol { margin: 0 0 ${spacing.xsmall}px; padding-left: ${spacing.medium}px; }
  li { margin-bottom: 2px; }
  strong { font-weight: 600; }
  code {
    font-family: monospace;
    font-size: 0.85em;
    background: ${color.backgroundNeutral50};
    border-radius: 3px;
    padding: 0.1em 0.3em;
  }
  pre {
    background: ${color.backgroundNeutral50};
    border-radius: 6px;
    padding: ${spacing.small}px;
    overflow-x: auto;
    margin: 0 0 ${spacing.xsmall}px;
  }
  blockquote {
    border-left: 3px solid ${color.borderLight};
    padding-left: ${spacing.small}px;
    color: ${color.textSecondary};
    margin: 0 0 ${spacing.xsmall}px;
  }
  table { width: 100%; border-collapse: collapse; margin: 0 0 ${spacing.xsmall}px; }
  th { text-align: left; padding: ${spacing.xsmall}px ${spacing.small}px; border-bottom: 2px solid ${color.borderNormal}; font-weight: 600; }
  td { padding: ${spacing.xsmall}px ${spacing.small}px; border-bottom: 1px solid ${color.borderLight}; }
`;

const FooterRow = styled.div`
  display: flex;
  gap: ${spacing.small}px;
  justify-content: flex-end;
  align-items: center;
  padding: ${spacing.small}px;
`;

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  documentId: string;
  editId: string;
  instruction: string;
  proposedContent: string;
  initialStatus: "pending" | "approved" | "rejected";
  onClose: () => void;
  onStatusChange: (status: "approved" | "rejected") => void;
}

export function EditDiffModal({
  documentId,
  editId,
  instruction,
  proposedContent,
  initialStatus,
  onClose,
  onStatusChange,
}: Props) {
  const qc = useQueryClient();
  const [localStatus, setLocalStatus] = useState(initialStatus);

  const { mutate: approve, isPending: approving } = useMutation({
    mutationFn: () => editsApi.approve(documentId, editId),
    onSuccess: () => {
      setLocalStatus("approved");
      onStatusChange("approved");
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["edits", documentId] });
      onClose();
    },
  });

  const { mutate: reject, isPending: rejecting } = useMutation({
    mutationFn: () => editsApi.reject(documentId, editId),
    onSuccess: () => {
      setLocalStatus("rejected");
      onStatusChange("rejected");
      qc.invalidateQueries({ queryKey: ["edits", documentId] });
      onClose();
    },
  });

  const busy = approving || rejecting;

  const Footer = () => (
    <FooterRow>
      <ButtonEmpty onClick={onClose} disabled={busy}>Close</ButtonEmpty>
      {localStatus === "pending" && (
        <>
          <ButtonDestructive
            icon={<CrossCircleFilled color={color.gray0} />}
            onClick={() => !busy && reject()}
            disabled={busy}
          >
            {rejecting ? "Rejecting…" : "Reject"}
          </ButtonDestructive>
          <ButtonPrimary
            icon={<CheckmarkCircleFilled color={color.gray0} />}
            onClick={() => !busy && approve()}
            disabled={busy}
          >
            {approving ? "Approving…" : "Approve"}
          </ButtonPrimary>
        </>
      )}
    </FooterRow>
  );

  return (
    <Modal
      headerText="Review Proposed Changes"
      size={MODAL_LARGE}
      onCancel={onClose}
      Footer={Footer}
    >
      <ModalBody>
        <Instruction>
          <strong>Requested:</strong> {instruction}
        </Instruction>
        <ContentPanel>
          <MarkdownContent>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{proposedContent}</ReactMarkdown>
          </MarkdownContent>
        </ContentPanel>
      </ModalBody>
    </Modal>
  );
}
