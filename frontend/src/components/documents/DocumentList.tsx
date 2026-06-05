import { useEffect, useState } from "react";
import styled, { keyframes } from "styled-components";
import { useDeleteDocument, useDocuments } from "@/hooks/useDocuments";
import type { Document, ProcessingJob } from "@/types";

function useElapsedTime(since: string) {
  const [elapsed, setElapsed] = useState(() => Math.floor((Date.now() - new Date(since).getTime()) / 1000));

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - new Date(since).getTime()) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [since]);

  const m = Math.floor(elapsed / 60);
  const s = elapsed % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

const TOTAL_STAGES = 4;

const STAGE_LABELS: Record<string, string> = {
  TEXT_EXTRACTION: "Extracting",
  CHUNKING: "Chunking",
  EMBEDDING: "Embedding",
  SUMMARIZATION: "Summarizing",
};

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

const ProgressTrack = styled.div`
  margin-top: 0.4rem;
  height: 4px;
  background: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
  max-width: 220px;
`;

const ProgressFill = styled.div<{ $pct: number; $active: boolean }>`
  height: 100%;
  width: ${({ $pct }) => $pct}%;
  background: #1565c0;
  border-radius: 2px;
  transition: width 0.4s ease;
  animation: ${({ $active }) => ($active ? pulse : "none")} 1.4s ease-in-out infinite;
`;

const ProgressFooter = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.2rem;
`;

const StageLabel = styled.span`
  font-size: 0.7rem;
  color: #1565c0;
`;

const ElapsedLabel = styled.span`
  font-size: 0.7rem;
  color: #999;
`;

function ProcessingProgress({ jobs, createdAt }: { jobs: ProcessingJob[]; createdAt: string }) {
  const elapsed = useElapsedTime(createdAt);
  const completed = jobs.filter((j) => j.status === "COMPLETED").length;
  const inProgress = jobs.find((j) => j.status === "IN_PROGRESS");
  const nextPending = jobs.find((j) => j.status === "PENDING");
  const activeJob = inProgress ?? nextPending;
  const pct = Math.round((completed / TOTAL_STAGES) * 100);
  const currentLabel = activeJob ? STAGE_LABELS[activeJob.stage] ?? activeJob.stage : null;

  return (
    <>
      <ProgressTrack>
        <ProgressFill $pct={pct} $active={!!inProgress} />
      </ProgressTrack>
      <ProgressFooter>
        <StageLabel>{currentLabel ? `${currentLabel}… ${pct}%` : ""}</StageLabel>
        <ElapsedLabel>{elapsed}</ElapsedLabel>
      </ProgressFooter>
    </>
  );
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: "#757575", PROCESSING: "#1565c0",
  COMPLETED: "#2e7d32", FAILED: "#c62828",
};

const StatusBadge = styled.span<{ $status: string }>`
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  background: ${({ $status }) => STATUS_COLORS[$status] ?? "#999"};
  color: #fff;
`;

const TableWrapper = styled.div`
  overflow-x: auto;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
`;

const Thead = styled.thead`
  background: #f5f5f5;
`;

const Th = styled.th`
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.8rem;
  color: #555;
  font-weight: 600;
`;

const Row = styled.tr<{ $selected: boolean; $clickable: boolean }>`
  border-bottom: 1px solid #e0e0e0;
  background: ${({ $selected }) => ($selected ? "#e8f0fe" : "transparent")};
  cursor: ${({ $clickable }) => ($clickable ? "pointer" : "not-allowed")};
  transition: background 0.15s;
`;

const Td = styled.td`
  padding: 0.75rem 1rem;
`;

const FilenameText = styled.span<{ $clickable: boolean }>`
  font-weight: 500;
  color: ${({ $clickable }) => ($clickable ? "#1a73e8" : "inherit")};
`;

const SummaryText = styled.p`
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: #666;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const MetaText = styled.td`
  padding: 0.75rem 1rem;
  color: #666;
  font-size: 0.875rem;
`;

const DeleteButton = styled.button`
  background: none;
  border: 1px solid #e53935;
  color: #e53935;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.75rem;
`;

const HintText = styled.p`
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #999;
`;

const StateText = styled.p<{ $color: string }>`
  color: ${({ $color }) => $color};
`;

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DocumentRowProps {
  doc: Document;
  isSelected: boolean;
  onSelect: (doc: Document) => void;
}

function DocumentRow({ doc, isSelected, onSelect }: DocumentRowProps) {
  const { mutate: deleteDoc } = useDeleteDocument();
  const isClickable = doc.status === "COMPLETED";

  return (
    <Row
      $selected={isSelected}
      $clickable={isClickable}
      onClick={() => isClickable && onSelect(doc)}
      title={isClickable ? "Click to chat about this document" : `Cannot chat — status is ${doc.status}`}
    >
      <Td>
        <FilenameText $clickable={isClickable}>{doc.filename}</FilenameText>
        {doc.summary && <SummaryText>{doc.summary}</SummaryText>}
        {(doc.status === "PROCESSING" || doc.status === "PENDING") && (
          <ProcessingProgress jobs={doc.processing_jobs} createdAt={doc.created_at} />
        )}
      </Td>
      <MetaText>{formatBytes(doc.file_size_bytes)}</MetaText>
      <Td><StatusBadge $status={doc.status}>{doc.status}</StatusBadge></Td>
      <MetaText>{new Date(doc.created_at).toLocaleDateString()}</MetaText>
      <Td>
        <DeleteButton onClick={(e) => { e.stopPropagation(); deleteDoc(doc.id); }}>
          Delete
        </DeleteButton>
      </Td>
    </Row>
  );
}

interface DocumentListProps {
  onSelect: (doc: Document) => void;
  selectedId?: string;
}

export function DocumentList({ onSelect, selectedId }: DocumentListProps) {
  const { data, isLoading, error } = useDocuments();

  if (isLoading) return <StateText $color="#666">Loading documents...</StateText>;
  if (error) return <StateText $color="#d32f2f">Failed to load documents.</StateText>;
  if (!data?.items.length) return <StateText $color="#999">No documents uploaded yet.</StateText>;

  return (
    <TableWrapper>
      <Table>
        <Thead>
          <tr>
            <Th>Filename</Th>
            <Th>Size</Th>
            <Th>Status</Th>
            <Th>Uploaded</Th>
            <Th />
          </tr>
        </Thead>
        <tbody>
          {data.items.map((doc) => (
            <DocumentRow
              key={doc.id}
              doc={doc}
              isSelected={doc.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </tbody>
      </Table>
      <HintText>Click a completed document to open chat</HintText>
    </TableWrapper>
  );
}
