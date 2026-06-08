import { DragEvent, useRef, useState } from "react";
import styled from "styled-components";
import { borderRadius, color, spacing, text } from "@planview/pv-utilities";
import { ButtonPrimary } from "@planview/pv-uikit";
import {
  Upload,
  Trash,
  CheckmarkCircle,
  CheckmarkCircleFilled,
  CrossCircleFilled,
  Spinner,
  MinusCircle,
  FilePdf,
  FileWord,
  FileText,
  FileImage,
  FileGeneral,
} from "@planview/pv-icons";
import { useUploadDocument } from "@/hooks/useDocuments";
import { useDocumentStatus } from "@/hooks/useWebSocket";
import { documentsApi } from "@/api/documents";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "text/plain",
  "text/markdown",
  "text/csv",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "application/vnd.ms-powerpoint",
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/tiff",
  "image/bmp",
  "image/webp",
  "image/gif",
];

const IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/tiff",
  "image/bmp",
  "image/webp",
  "image/gif",
]);

// ── Styled components ─────────────────────────────────────────────────────────

const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: ${spacing.xsmall}px ${spacing.small}px;
  background: ${color.backgroundNeutral50};
  border-radius: 6px 6px 0 0;
  border: 1px solid ${color.borderLight};
  border-bottom: none;
  ${text.small};
  color: ${color.textSecondary};
`;

const FileList = styled.div`
  border: 1px solid ${color.borderLight};
  border-bottom: none;
  flex: 1;
  overflow-y: auto;
`;

const FileRow = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.small}px;
  padding: ${spacing.small}px;
  border-bottom: 1px solid ${color.borderLight};
  background: ${color.backgroundNeutral0};
`;

const FileInfo = styled.div`
  flex: 1;
  min-width: 0;
`;

const FileName = styled.div`
  ${text.regular};
  font-weight: 500;
  color: ${color.textPrimary};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const FileStatus = styled.div<{ $error?: boolean }>`
  ${text.small};
  color: ${({ $error }) => ($error ? color.textError : color.textSecondary)};
  margin-top: 2px;
`;

const ProgressBar = styled.div`
  height: 3px;
  background: ${color.borderLight};
  ${borderRadius.small()};
  margin-top: 4px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ $pct: number }>`
  height: 100%;
  width: ${({ $pct }) => $pct}%;
  background: ${color.backgroundPrimary};
  transition: width 0.2s;
`;

const IconBtn = styled.button`
  background: none;
  border: none;
  cursor: pointer;
  color: ${color.textSecondary};
  padding: 2px 4px;
  font-size: 1rem;
  line-height: 1;
  flex-shrink: 0;
  &:hover {
    color: ${color.textPrimary};
  }
`;

const PipelinePanel = styled.div`
  padding: ${spacing.xsmall}px ${spacing.small}px ${spacing.small}px 3rem;
  background: ${color.backgroundNeutral50};
  border-bottom: 1px solid ${color.borderLight};
`;

const StageList = styled.div`
  display: flex;
  gap: ${spacing.xsmall}px;
  flex-wrap: wrap;
  margin-top: ${spacing.xsmall}px;
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
          const stageColor =
            job.status === "COMPLETED"
              ? "#2e7d32"
              : job.status === "FAILED"
                ? color.textError
                : job.status === "IN_PROGRESS"
                  ? color.backgroundPrimary
                  : color.textSecondary;
          const StageIcon =
            job.status === "COMPLETED"
              ? CheckmarkCircleFilled
              : job.status === "FAILED"
                ? CrossCircleFilled
                : job.status === "IN_PROGRESS"
                  ? Spinner
                  : MinusCircle;
          return (
            <span key={job.stage} style={{ display: "flex", alignItems: "center", gap: 3 }}>
              <StageIcon size={14} color={stageColor} />
              <span style={{ fontSize: "0.72rem", color: stageColor }}>{STAGE_LABELS[job.stage] || job.stage}</span>
            </span>
          );
        })}
      </StageList>
      {isComplete && (
        <div
          style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.72rem", color: "#2e7d32", marginTop: 4 }}
        >
          <CheckmarkCircle size={14} color="#2e7d32" />
          Ready for search and Q&amp;A
        </div>
      )}
    </PipelinePanel>
  );
}

const DropZone = styled.div<{ $dragging: boolean }>`
  border: 2px dashed ${({ $dragging }) => ($dragging ? color.backgroundPrimary : color.borderLight)};
  border-radius: 8px;
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: ${spacing.xsmall}px;
  cursor: pointer;
  background: ${({ $dragging }) => ($dragging ? color.primary0 : color.backgroundNeutral0)};
  transition:
    background 0.15s,
    border-color 0.15s;
  height: 100%;
  box-sizing: border-box;
`;

const ChooseRow = styled.div`
  padding: ${spacing.small}px;
  display: flex;
  justify-content: center;
  border: 1px solid ${color.borderLight};
  border-radius: 0 0 6px 6px;
  background: ${color.backgroundNeutral50};
`;

const HiddenInput = styled.input`
  display: none;
`;

const ErrorBanner = styled.div`
  ${text.small};
  color: ${color.textError};
  padding: ${spacing.xsmall}px ${spacing.small}px;
  background: ${color.backgroundError};
  border: 1px solid ${color.borderLight};
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
        setBannerError(
          `"${file.name}" is not a supported type (PDF, DOCX, XLSX, PPTX, TXT, MD, CSV, PNG, JPG, TIFF, BMP, WebP, GIF).`,
        );
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

    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeItem = async (item: UploadItem) => {
    if (item.documentId) {
      await documentsApi.delete(item.documentId).catch(() => {});
      onRemoved?.(item.documentId);
    }
    setItems((prev) => prev.filter((i) => i.localId !== item.localId));
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

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
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={40} color={color.textSecondary} />
        <span style={{ fontSize: "0.95rem", fontWeight: 500, color: color.textPrimary }}>Drag and drop files here</span>
        <span style={{ fontSize: "0.875rem", color: color.textSecondary }}>or</span>
        <ButtonPrimary
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          }}
        >
          Choose files
        </ButtonPrimary>
        <span style={{ fontSize: "0.75rem", color: color.textSecondary, textAlign: "center" }}>
          PDF, DOCX, XLSX, PPTX, TXT, MD, CSV · PNG, JPG, TIFF, BMP, WebP, GIF
        </span>
        <HiddenInput
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls,.pptx,.ppt,.png,.jpg,.jpeg,.tiff,.tif,.bmp,.webp,.gif"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </DropZone>
    );
  }

  return (
    <Wrapper
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
    >
      <Header>
        <span>
          Uploading {uploadingCount} file{uploadingCount !== 1 ? "s" : ""}
        </span>
        <span>
          {fmtBytes(uploadedBytes)}/{fmtBytes(totalBytes)} uploaded
        </span>
      </Header>

      <FileList>
        {items.map((item) => (
          <div key={item.localId}>
            <FileRow>
              {fileExt(item.file) === "pdf" ? (
                <FilePdf />
              ) : fileExt(item.file) === "docx" || fileExt(item.file) === "doc" ? (
                <FileWord />
              ) : fileExt(item.file) === "txt" ? (
                <FileText />
              ) : IMAGE_TYPES.has(item.file.type) ? (
                <FileImage />
              ) : (
                <FileGeneral />
              )}
              <FileInfo>
                <FileName title={item.file.name}>{item.file.name}</FileName>
                {item.status === "uploading" ? (
                  <>
                    <FileStatus>{item.progress}% uploading…</FileStatus>
                    <ProgressBar>
                      <ProgressFill $pct={item.progress} />
                    </ProgressBar>
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
                <Trash size={16} />
              </IconBtn>
            </FileRow>
            {item.expanded && item.documentId && <PipelineRow documentId={item.documentId} />}
          </div>
        ))}
      </FileList>

      {bannerError && <ErrorBanner>{bannerError}</ErrorBanner>}

      <ChooseRow>
        <ButtonPrimary onClick={() => fileInputRef.current?.click()}>Choose files</ButtonPrimary>
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
