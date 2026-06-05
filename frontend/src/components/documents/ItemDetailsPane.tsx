import { useEffect, useState } from "react";
import styled from "styled-components";
import { DetailsPanel, DetailsPanelSection } from "@planview/pv-details";
import { AssistedChat, Info } from "@planview/pv-icons";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { DescriptionEditor } from "./DescriptionEditor";
import type { DocumentItem, FolderItem, UnifiedItem } from "@/types";

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
  gap: 6px 12px;
  margin: 0 0 16px;
  font-size: 0.82rem;
`;

const MetaLabel = styled.dt`
  color: #666;
  font-weight: 500;
  white-space: nowrap;
`;

const MetaValue = styled.dd`
  margin: 0;
  color: #222;
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

export function ItemDetailsPane({ item, activeTab: externalTab = "details", onClose }: ItemDetailsPaneProps) {
  const [activeTab, setActiveTab] = useState<string>(externalTab);

  useEffect(() => {
    setActiveTab(externalTab);
  }, [item.id, externalTab]);

  const isDoc = item.type === "document";
  const doc = isDoc ? (item as DocumentItem) : null;
  const folder = !isDoc ? (item as FolderItem) : null;
  const canChat = !!doc && doc.status === "COMPLETED";

  const tabs = [
    { id: "details", label: "Details", icon: <Info /> },
    ...(canChat ? [{ id: "chat", label: "Chat", icon: <AssistedChat /> }] : []),
  ];

  return (
    <DetailsPanel
      header={doc ? doc.filename : folder!.name}
      onClose={onClose}
      tabs={tabs}
      activeTab={activeTab}
      onActivateTab={setActiveTab}
    >
      {activeTab === "details" && (
        <>
          <DetailsPanelSection label="Description">
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
                  <MetaValue>{formatBytes(doc.file_size_bytes)}</MetaValue>

                  <MetaLabel>Status</MetaLabel>
                  <MetaValue>{doc.status}</MetaValue>

                  {doc.folder_name && (
                    <>
                      <MetaLabel>Folder</MetaLabel>
                      <MetaValue>{doc.folder_name}</MetaValue>
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
                          style={{ color: "#1a73e8", wordBreak: "break-all" }}
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
          <ChatWindow documentId={doc!.id} documentName={doc!.filename} />
        </ChatFill>
      )}
    </DetailsPanel>
  );
}
