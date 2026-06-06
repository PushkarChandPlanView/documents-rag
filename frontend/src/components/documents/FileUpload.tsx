import { DragEvent, useRef, useState } from "react";
import styled from "styled-components";
import { ButtonPrimary } from "@planview/pv-uikit";
import { useUploadDocument } from "@/hooks/useDocuments";
import { useDocumentStatus } from "@/hooks/useWebSocket";
import { documentsApi } from "@/api/documents";

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
];

// ── Styled components ─────────────────────────────────────────────────────────

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 260px;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: #f5f5f5;
  border-radius: 6px 6px 0 0;
  border: 1px solid #e0e0e0;
  border-bottom: none;
  font-size: 0.8rem;
  color: #555;
`;

const FileList = styled.div`
  border: 1px solid #e0e0e0;
  border-bottom: none;
  flex: 1;
`;

const FileRow = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
`;

const FileIconBox = styled.div<{ $ext: string }>`
  width: 32px;
  height: 32px;
  border-radius: 4px;
  background: ${({ $ext }) =>
    $ext === "pdf" ? "#e53935" : $ext === "docx" || $ext === "doc" ? "#1565c0" : "#555"};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
  text-transform: uppercase;
`;

const FileInfo = styled.div`
  flex: 1;
  min-width: 0;
`;

const FileName = styled.div`
  font-size: 0.825rem;
  font-weight: 500;
  color: #222;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const FileStatus = styled.div<{ $error?: boolean }>`
  font-size: 0.72rem;
  color: ${({ $error }) => ($error ? "#c62828" : "#555")};
  margin-top: 2px;
`;

const ProgressBar = styled.div`
  height: 3px;
  background: #e0e0e0;
  border-radius: 2px;
  margin-top: 4px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ $pct: number }>`
  height: 100%;
  width: ${({ $pct }) => $pct}%;
  background: #1a73e8;
  transition: width 0.2s;
`;

const IconBtn = styled.button`
  background: none;
  border: none;
  cursor: pointer;
  color: #777;
  padding: 2px 4px;
  font-size: 1rem;
  line-height: 1;
  flex-shrink: 0;
  &:hover { color: #333; }
`;

// Pipeline expand panel
const PipelinePanel = styled.div`
  padding: 0.5rem 0.75rem 0.75rem 3rem;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
`;

const StageList = styled.div`
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
`;

const StageDot = styled.span<{ $color: string }>`
  color: ${({ $color }) => $color};
  font-size: 0.72rem;
  font-weight: 600;
`;

const STAGE_LABELS: Record<string, string> = {
  TEXT_EXTRACTION: "Extract",
  CHUNKING: "Chunk",
  EMBEDDING: "Embed",
  SUMMARIZATION: "Summarize",
};

function PipelineRow({ documentId }: { documentId: string }) {
  const { stages, isComplete } = useDocumentStatus(documentId);
  if (!stages.length) return null;
  return (
    <PipelinePanel>
      <StageList>
        {stages.map((job) => {
          const color =
            job.status === "COMPLETED" ? "#2e7d32"
            : job.status === "FAILED"  ? "#c62828"
            : job.status === "IN_PROGRESS" ? "#1565c0"
            : "#9e9e9e";
          return (
            <span key={job.stage} style={{ display: "flex", alignItems: "center", gap: 3 }}>
              <StageDot $color={color}>●</StageDot>
              <span style={{ fontSize: "0.72rem", color }}>{STAGE_LABELS[job.stage] || job.stage}</span>
            </span>
          );
        })}
      </StageList>
      {isComplete && (
        <div style={{ fontSize: "0.72rem", color: "#2e7d32", marginTop: 4 }}>
          ✓ Ready for search and Q&amp;A
        </div>
      )}
    </PipelinePanel>
  );
}

// Drop zone (shown when no files yet)
const DropZone = styled.div<{ $dragging: boolean }>`
  border: 2px dashed ${({ $dragging }) => ($dragging ? "#1a73e8" : "#ccc")};
  border-radius: 8px;
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  background: ${({ $dragging }) => ($dragging ? "#e8f0fe" : "#fff")};
  transition: background 0.15s, border-color 0.15s;
  min-height: 260px;
`;

const ChooseRow = styled.div`
  padding: 0.75rem;
  display: flex;
  justify-content: center;
  border: 1px solid #e0e0e0;
  border-radius: 0 0 6px 6px;
  background: #fafafa;
`;

const HiddenInput = styled.input`
  display: none;
`;

const ErrorBanner = styled.div`
  font-size: 0.8rem;
  color: #c62828;
  padding: 0.25rem 0.75rem;
  background: #fff3f3;
  border: 1px solid #e0e0e0;
`;

// ── Types ─────────────────────────────────────────────────────────────────────

interface UploadItem {
  localId: string;
  file: File;
  progress: number;
  status: "uploading" | "done" | "error";
  documentId?: string;
  expanded: boolean;
}

interface FileUploadProps {
  onUploaded?: (docId: string) => void;
  onRemoved?: (docId: string) => void;
  folderId?: string;
}

// ── Helper ────────────────────────────────────────────────────────────────────

function fileExt(file: File): string {
  return file.name.split(".").pop()?.toLowerCase() ?? "";
}

function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function FileUpload({ onUploaded, onRemoved, folderId }: FileUploadProps) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { mutateAsync: upload } = useUploadDocument();

  const updateItem = (localId: string, patch: Partial<UploadItem>) =>
    setItems((prev) => prev.map((i) => (i.localId === localId ? { ...i, ...patch } : i)));

  const startUpload = async (item: UploadItem) => {
    try {
      const res = await upload({
        file: item.file,
        onProgress: (pct) => updateItem(item.localId, { progress: pct }),
        folderId,
      });
      updateItem(item.localId, { status: "done", documentId: res.document_id, progress: 100 });
      onUploaded?.(res.document_id);
    } catch {
      updateItem(item.localId, { status: "error" });
    }
  };

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBannerError(null);

    const newItems: UploadItem[] = [];
    for (const file of Array.from(files)) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        setBannerError(`"${file.name}" is not a supported type (PDF, DOCX, TXT).`);
        continue;
      }
      if (file.size > 100 * 1024 * 1024) {
        setBannerError(`"${file.name}" exceeds the 100 MB limit.`);
        continue;
      }
      newItems.push({ localId: crypto.randomUUID(), file, progress: 0, status: "uploading", expanded: false });
    }

    if (newItems.length === 0) return;
    setItems((prev) => [...prev, ...newItems]);
    newItems.forEach(startUpload);

    // reset input so same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeItem = async (item: UploadItem) => {
    if (item.documentId) {
      await documentsApi.delete(item.documentId).catch(() => {});
      onRemoved?.(item.documentId);
    }
    setItems((prev) => prev.filter((i) => i.localId !== item.localId));
  };

  const toggleExpand = (localId: string) =>
    setItems((prev) => prev.map((i) => (i.localId === localId ? { ...i, expanded: !i.expanded } : i)));

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  // Header stats
  const uploadingCount = items.filter((i) => i.status === "uploading").length;
  const totalBytes = items.reduce((s, i) => s + i.file.size, 0);
  const uploadedBytes = items.reduce((s, i) => {
    if (i.status === "done") return s + i.file.size;
    if (i.status === "uploading") return s + Math.round((i.file.size * i.progress) / 100);
    return s;
  }, 0);

  if (items.length === 0) {
    return (
      <DropZone
        $dragging={isDragging}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <span style={{ fontSize: "0.95rem", fontWeight: 500, color: "#333" }}>
          Drag and drop files here
        </span>
        <span style={{ fontSize: "0.875rem", color: "#888" }}>or</span>
        <ButtonPrimary onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>
          Choose files
        </ButtonPrimary>
        <HiddenInput
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.txt"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </DropZone>
    );
  }

  return (
    <Wrapper
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
    >
      <Header>
        <span>Uploading {uploadingCount} file{uploadingCount !== 1 ? "s" : ""}</span>
        <span>{fmtBytes(uploadedBytes)}/{fmtBytes(totalBytes)} uploaded</span>
      </Header>

      <FileList>
        {items.map((item) => (
          <div key={item.localId}>
            <FileRow>
              <FileIconBox $ext={fileExt(item.file)}>
                {fileExt(item.file) || "?"}
              </FileIconBox>
              <FileInfo>
                <FileName title={item.file.name}>{item.file.name}</FileName>
                {item.status === "uploading" ? (
                  <>
                    <FileStatus>{item.progress}% uploading…</FileStatus>
                    <ProgressBar><ProgressFill $pct={item.progress} /></ProgressBar>
                  </>
                ) : item.status === "done" ? (
                  <FileStatus>Uploaded successfully</FileStatus>
                ) : (
                  <FileStatus $error>Upload failed — click × to remove</FileStatus>
                )}
              </FileInfo>
              <IconBtn
                title="Remove"
                onClick={() => removeItem(item)}
                disabled={item.status === "uploading"}
                style={{ opacity: item.status === "uploading" ? 0.3 : 1 }}
              >
                ×
              </IconBtn>
              {item.status === "done" && item.documentId && (
                <IconBtn
                  title={item.expanded ? "Collapse" : "Show processing stages"}
                  onClick={() => toggleExpand(item.localId)}
                >
                  {item.expanded ? "▾" : "›"}
                </IconBtn>
              )}
            </FileRow>
            {item.expanded && item.documentId && (
              <PipelineRow documentId={item.documentId} />
            )}
          </div>
        ))}
      </FileList>

      {bannerError && <ErrorBanner>{bannerError}</ErrorBanner>}

      <ChooseRow>
        <ButtonPrimary onClick={() => fileInputRef.current?.click()}>
          Choose files
        </ButtonPrimary>
      </ChooseRow>

      <HiddenInput
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.txt"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </Wrapper>
  );
}
