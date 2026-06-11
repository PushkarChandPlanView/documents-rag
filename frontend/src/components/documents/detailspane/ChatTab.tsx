import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { AiAnvi, Info, WarningFilled } from "@planview/pv-icons";
import { ChatWindow } from "@/components/chat/ChatWindow";
import type { DocumentItem } from "@/types";

// ── Placeholder ───────────────────────────────────────────────────────────────

const Placeholder = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: ${spacing.medium}px;
  height: 100%;
  padding: ${spacing.xlarge}px;
  text-align: center;
  color: ${color.textSecondary};
  ${text.regular};

  svg { width: 32px; height: 32px; flex-shrink: 0; }
`;

const PlaceholderTitle = styled.div`
  font-weight: 600;
  color: ${color.textPrimary};
`;

const PlaceholderSub = styled.div`
  ${text.small};
  color: ${color.textSecondary};
  max-width: 280px;
`;

const STATUS_CONFIG: Record<string, { icon: JSX.Element; title: string; sub: string }> = {
  PENDING: {
    icon: <Info color={color.info400} />,
    title: "Document queued",
    sub:   "The document is waiting to be processed. Chat will be available once complete.",
  },
  PROCESSING: {
    icon: <AiAnvi color="anvi" />,
    title: "Processing document…",
    sub:   "We're extracting and indexing the content. Come back in a moment.",
  },
  FAILED: {
    icon: <WarningFilled color={color.error400} />,
    title: "Processing failed",
    sub:   "The document could not be processed. Use the Reprocess button in the Details tab.",
  },
};

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  doc: DocumentItem;
}

export const ChatTab = ({ doc }: Props) => {
  if (doc.status === "COMPLETED") {
    return <ChatWindow documentId={doc.id} documentName={doc.name} />;
  }

  const cfg = STATUS_CONFIG[doc.status ?? ""] ?? {
    icon: <Info color={color.info400} />,
    title: "Not ready",
    sub:   "The document is not yet available for chat.",
  };

  return (
    <Placeholder>
      {cfg.icon}
      <div>
        <PlaceholderTitle>{cfg.title}</PlaceholderTitle>
        <PlaceholderSub>{cfg.sub}</PlaceholderSub>
      </div>
    </Placeholder>
  );
};
