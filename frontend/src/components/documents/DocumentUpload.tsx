import { DragEvent, useRef, useState } from "react";
import styled from "styled-components";
import { useUploadDocument } from "@/hooks/useDocuments";
import { useDocumentStatus } from "@/hooks/useWebSocket";

const ACCEPTED_TYPES = ["application/pdf", "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword"];

const STAGE_LABELS: Record<string, string> = {
  TEXT_EXTRACTION: "Extract Text",
  CHUNKING: "Chunk",
  EMBEDDING: "Embed",
  SUMMARIZATION: "Summarize",
};

const PipelineWrapper = styled.div`
  margin-top: 1rem;
  padding: 1rem;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
`;

const PipelineTitle = styled.p`
  margin: 0 0 0.75rem;
  font-weight: 600;
  font-size: 0.875rem;
`;

const StageList = styled.div`
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
`;

const StageItem = styled.div`
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
`;

const StageDot = styled.span<{ $color: string }>`
  color: ${({ $color }) => $color};
  font-weight: 600;
`;

const StageLabel = styled.span<{ $color: string }>`
  color: ${({ $color }) => $color};
`;

const CompleteText = styled.p`
  margin: 0.5rem 0 0;
  color: #2e7d32;
  font-size: 0.75rem;
`;

const DropZone = styled.div<{ $dragging: boolean }>`
  border: 2px dashed ${({ $dragging }) => ($dragging ? "#1a73e8" : "#ccc")};
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  background: ${({ $dragging }) => ($dragging ? "#e8f0fe" : "#fafafa")};
  transition: all 0.2s;
`;

const DropHint = styled.p`
  margin: 0;
  color: #666;
  font-size: 0.9rem;
`;

const DropSubHint = styled.p`
  margin: 0.5rem 0 0;
  color: #999;
  font-size: 0.75rem;
`;

const HiddenInput = styled.input`
  display: none;
`;

const ProgressWrapper = styled.div`
  margin-top: 1rem;
`;

const ProgressTrack = styled.div`
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
`;

const ProgressFill = styled.div<{ $pct: number }>`
  height: 100%;
  width: ${({ $pct }) => $pct}%;
  background: #1a73e8;
  transition: width 0.3s;
`;

const ProgressLabel = styled.p`
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: #666;
`;

const ErrorText = styled.p`
  margin-top: 0.75rem;
  color: #d32f2f;
  font-size: 0.875rem;
`;

function PipelineStatus({ documentId }: { documentId: string }) {
  const { stages, isComplete } = useDocumentStatus(documentId);
  if (!stages.length) return null;

  return (
    <PipelineWrapper>
      <PipelineTitle>Processing Pipeline</PipelineTitle>
      <StageList>
        {stages.map((job) => {
          const color = job.status === "COMPLETED" ? "#2e7d32" : job.status === "FAILED" ? "#c62828" : job.status === "IN_PROGRESS" ? "#1565c0" : "#757575";
          return (
            <StageItem key={job.stage}>
              <StageDot $color={color}>●</StageDot>
              <StageLabel $color={color}>{STAGE_LABELS[job.stage] || job.stage}</StageLabel>
            </StageItem>
          );
        })}
      </StageList>
      {isComplete && <CompleteText>✓ Document ready for search and Q&A</CompleteText>}
    </PipelineWrapper>
  );
}

export function DocumentUpload() {
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { mutateAsync: upload } = useUploadDocument();

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError("Unsupported file type. Please upload PDF, DOCX, or TXT.");
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      setError("File too large. Maximum size is 100MB.");
      return;
    }
    setError(null);
    setProgress(0);
    setUploadedDocId(null);
    try {
      const res = await upload({ file, onProgress: setProgress });
      setUploadedDocId(res.document_id);
      setProgress(null);
    } catch {
      setError("Upload failed. Please try again.");
      setProgress(null);
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div>
      <DropZone
        $dragging={isDragging}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <DropHint>Drag & drop a PDF, DOCX, or TXT file here, or click to browse</DropHint>
        <DropSubHint>Maximum 100MB</DropSubHint>
      </DropZone>
      <HiddenInput
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {progress !== null && (
        <ProgressWrapper>
          <ProgressTrack>
            <ProgressFill $pct={progress} />
          </ProgressTrack>
          <ProgressLabel>{progress}% uploaded</ProgressLabel>
        </ProgressWrapper>
      )}
      {error && <ErrorText>{error}</ErrorText>}
      {uploadedDocId && <PipelineStatus documentId={uploadedDocId} />}
    </div>
  );
}
