import { useEffect, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { DetailsPanel, DetailsPanelSection } from "@planview/pv-details";
import {
  AiAnvi,
  CheckmarkCircle,
  FileExcel,
  FileImage,
  FilePdf,
  FilePowerpoint,
  FileText,
  FileWord,
  Folder,
  Info,
  Link,
  Refresh,
  Comment,
  History
} from "@planview/pv-icons";
import { ButtonEmpty } from "@planview/pv-uikit";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ComplianceTab } from "@/components/compliance/ComplianceTab";
import { EditHistoryList } from "./EditHistoryList";
import { DescriptionEditor } from "./DescriptionEditor";
import { useReprocessDocument } from "@/hooks/useDocuments";
import { useDocumentEdits } from "@/hooks/useEdits";
import type { DocumentItem, FolderItem, UnifiedItem } from "@/types";
import { NameField } from "./NameField";
import { IMAGE_MIMES } from "@/constants";
import CommentsTab from "./Comments";

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

export type DetailTab = "details" | "preview" | "chat" | "compliance" | "history" | "comments";

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
  const { data: editsData } = useDocumentEdits(doc?.id);
  const currentVersion = editsData?.edits
    .filter((e) => e.status === "approved" && e.version != null)
    .reduce((max, e) => Math.max(max, e.version!), 0) || null;

  const tabs = [
    { id: "details", label: "Details", icon: <Info /> },
    ...(canChat ? [{ id: "chat", label: "Chat", icon: <AiAnvi color="anvi" /> }] : []),
    ...(canChat ? [{ id: "compliance", label: "Compliance", icon: <CheckmarkCircle /> }] : []),
    ...(canChat ? [{ id: "comments", label: "Comments", icon: <Comment /> }] : []),
    ...(canChat ? [{ id: "history", label: "History", icon: <History /> }] : []),
  ];

  const getSelection = (item: UnifiedItem) => {
    if (item.type === "document") {
      const mime = item.mime_type;
      if (mime === "text/html") return <Link />;
      if (
        mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
        mime === "application/msword"
      )
        return <FileWord />;
      if (
        mime === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
        mime === "application/vnd.ms-excel"
      )
        return <FileExcel />;
      if (
        mime === "application/vnd.openxmlformats-officedocument.presentationml.presentation" ||
        mime === "application/vnd.ms-powerpoint"
      )
        return <FilePowerpoint />;
      if (mime === "application/pdf") return <FilePdf />;
      if (mime && IMAGE_MIMES.includes(mime)) return <FileImage />;
      return <FileText />;
    }
    return <Folder />;
  };

  return (
    <DetailsPanel
      header={{
        label: item.name,
        icon: getSelection(item),
      }}
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
                  <MetaValue>{doc.file_size_bytes !== null ? formatBytes(doc.file_size_bytes) : "N/A"}</MetaValue>

                  <MetaLabel>Status</MetaLabel>
                  <MetaValue>{doc.status}</MetaValue>

                  {currentVersion != null && (
                    <>
                      <MetaLabel>Version</MetaLabel>
                      <MetaValue>v{currentVersion}</MetaValue>
                    </>
                  )}

                  {canReprocess && (
                    <>
                      <MetaLabel />
                      <MetaValue>
                        <ButtonEmpty icon={<Refresh />} onClick={() => reprocess(doc!.id)} disabled={reprocessing}>
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

      {activeTab === "compliance" && canChat && (
        <ChatFill>
          <ComplianceTab documentId={doc!.id} />
        </ChatFill>
      )}

      {activeTab === "history" && canChat && (
        <ChatFill>
          <EditHistoryList documentId={doc!.id} />
        </ChatFill>
      )}
        {activeTab === "comments" && canChat && (
        <ChatFill>
          <CommentsTab documentId={doc!.id} />
        </ChatFill>
      )}
    </DetailsPanel>
  );
}
