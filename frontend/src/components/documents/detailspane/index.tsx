import { useEffect, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { DetailsPanel, DetailsPanelSection } from "@planview/pv-details";
import { AiAnvi, Info, Refresh } from "@planview/pv-icons";
import { ButtonEmpty } from "@planview/pv-uikit";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { DescriptionEditor } from "./DescriptionEditor";
import { useReprocessDocument } from "@/hooks/useDocuments";
import type { DocumentItem, FolderItem, UnifiedItem } from "@/types";
import { NameField } from "./NameField";

// ── helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// ── styles ────────────────────────────────────────────────────────────────────

const MetaGrid = styled.dl`
  display: grid;
  grid-template-columns: auto 1fr;
  gap: ${spacing.xsmall}px ${spacing.small}px;
  margin: 0 0 ${spacing.medium}px;
  ${text.small};
`;

const MetaLabel = styled.dt`
  color: ${color.textSecondary};
  font-weight: 500;
  white-space: nowrap;
`;

const MetaValue = styled.dd`
  margin: 0;
  color: ${color.textPrimary};
  word-break: break-word;
`;

const ChatFill = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  overflow: hidden;
`;

// ── component ─────────────────────────────────────────────────────────────────

export type DetailTab = "details" | "chat";

interface ItemDetailsPaneProps {
  item: UnifiedItem;
  activeTab?: DetailTab;
  onClose: () => void;
}

export function DetailsPane({ item, activeTab: externalTab = "details", onClose }: ItemDetailsPaneProps) {
  const [activeTab, setActiveTab] = useState<string>(externalTab);

  useEffect(() => {
    setActiveTab(externalTab);
  }, [item.id, externalTab]);

  const isDoc = item.type === "document";
  const doc = isDoc ? (item as DocumentItem) : null;
  const folder = !isDoc ? (item as FolderItem) : null;
  const canChat = !!doc && doc.status === "COMPLETED";
  const canReprocess = !!doc && (doc.status === "FAILED" || doc.status === "PROCESSING");
  const { mutate: reprocess, isPending: reprocessing } = useReprocessDocument();

  const tabs = [
    { id: "details", label: "Details", icon: <Info /> },
    ...(canChat ? [{ id: "chat", label: "Chat", icon: <AiAnvi color="anvi" /> }] : []),
  ];

  return (
    <DetailsPanel
      header={item.name}
      onClose={onClose}
      tabs={tabs}
      activeTab={activeTab}
      onActivateTab={setActiveTab}
    >
      {activeTab === "details" && (
        <>
          <DetailsPanelSection label="Description">
            <NameField itemId={item.id} itemType={isDoc ? "document" : "folder"} value={item.name} />
            <DescriptionEditor
              itemId={item.id}
              itemType={isDoc ? "document" : "folder"}
              value={doc?.description ?? folder?.description ?? null}
            />
          </DetailsPanelSection>

          <DetailsPanelSection label="Properties">
            <MetaGrid>
              <MetaLabel>Type</MetaLabel>
              <MetaValue>{isDoc ? "Document" : "Folder"}</MetaValue>

              {doc && (
                <>
                  <MetaLabel>MIME type</MetaLabel>
                  <MetaValue>{doc.mime_type}</MetaValue>

                  <MetaLabel>Size</MetaLabel>
                  <MetaValue>{doc.file_size_bytes !== null ? formatBytes(doc.file_size_bytes) : 'N/A'}</MetaValue>

                  <MetaLabel>Status</MetaLabel>
                  <MetaValue>{doc.status}</MetaValue>

                  {canReprocess && (
                    <>
                      <MetaLabel />
                      <MetaValue>
                        <ButtonEmpty
                          icon={<Refresh />}
                          onClick={() => reprocess(doc!.id)}
                          disabled={reprocessing}
                        >
                          {reprocessing ? "Reprocessing…" : "Reprocess"}
                        </ButtonEmpty>
                      </MetaValue>
                    </>
                  )}

                  {item.parent_name && (
                    <>
                      <MetaLabel>Folder</MetaLabel>
                      <MetaValue>{item.parent_name}</MetaValue>
                    </>
                  )}

                  {doc.source_url && (
                    <>
                      <MetaLabel>URL</MetaLabel>
                      <MetaValue>
                        <a
                          href={doc.source_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: color.backgroundPrimary, wordBreak: "break-all" }}
                        >
                          {doc.source_url}
                        </a>
                      </MetaValue>
                    </>
                  )}
                </>
              )}

              <MetaLabel>Created</MetaLabel>
              <MetaValue>{fmtDate(item.created_at)}</MetaValue>

              <MetaLabel>Updated</MetaLabel>
              <MetaValue>{fmtDate(item.updated_at)}</MetaValue>
            </MetaGrid>
          </DetailsPanelSection>
        </>
      )}

      {activeTab === "chat" && canChat && (
        <ChatFill>
          <ChatWindow documentId={doc!.id} documentName={doc!.name} />
        </ChatFill>
      )}
    </DetailsPanel>
  );
}
