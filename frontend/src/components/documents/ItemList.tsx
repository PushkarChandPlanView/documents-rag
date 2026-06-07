import React, { useMemo, useState } from "react";
import styled from "styled-components";
import { color, spacing, text } from "@planview/pv-utilities";
import { Grid, GridCellBase } from "@planview/pv-grid";
import type { Column } from "@planview/pv-grid";
import type { GridRowMeta } from "@planview/pv-grid";
import { DESTRUCTIVE, Modal } from "@planview/pv-uikit";
import { ButtonAnviEmptyInverse, ButtonPrimary, ListItem } from "@planview/pv-uikit";
import {
  AiAnvi,
  FileExcel,
  FilePdf,
  FilePowerpoint,
  FileText,
  FileWord,
  Folder,
  Link,
  Trash,
} from "@planview/pv-icons";
import { useDeleteDocument, useDeleteFolder, useDocuments } from "@/hooks/useDocuments";
import type { DocumentItem, FolderItem, UnifiedItem } from "@/types";
import type { ItemFiltersState } from "./ItemFilters";

// ── Row model ─────────────────────────────────────────────────────────────────

type DocRow = {
  id: string;
  parentId: string | null;
  index: number;
  name: string;
  fileType: string;
  size: string;
  status: string;
  uploadedAt: string;
  _doc?: DocumentItem;
  _folder?: FolderItem;
};

type DocRowMeta = GridRowMeta<DocRow>;

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const MIME_LABELS: Record<string, string> = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
  "application/msword": "Word",
  "text/plain": "Text",
  "text/markdown": "Markdown",
  "text/csv": "CSV",
  "text/html": "Link",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
  "application/vnd.ms-excel": "Excel",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint",
  "application/vnd.ms-powerpoint": "PowerPoint",
};

const FILE_TYPE_MIMES: Record<string, string[]> = {
  pdf: ["application/pdf"],
  word: ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"],
  text: ["text/plain"],
  markdown: ["text/markdown"],
  csv: ["text/csv"],
  excel: ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"],
  powerpoint: [
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
  ],
};

function getMimeLabel(mime: string) {
  return MIME_LABELS[mime] ?? mime.split("/")[1]?.toUpperCase() ?? "Other";
}

function getMimeIcon(mime: string): React.ReactNode {
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
  return <FileText />;
}

const IconWrapper = styled.span`
  display: inline-flex;
  align-items: center;
  gap: ${spacing.xsmall}px;
  svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    opacity: 0.7;
  }
`;

function unifiedToRows(items: UnifiedItem[], rootFolderId?: string): DocRow[] {
  const rows: DocRow[] = [];
  const apiFolderIds = new Set(items.filter((i): i is FolderItem => i.type === "folder").map((f) => f.id));

  items.forEach((item, i) => {
    if (item.type === "folder") {
      const parentId = rootFolderId ? (item.parent_id === rootFolderId ? null : item.parent_id) : item.parent_id;
      rows.push({
        id: item.id,
        parentId,
        index: i,
        name: item.name,
        fileType: "",
        size: "",
        status: "",
        uploadedAt: new Date(item.created_at).toLocaleDateString(),
        _folder: item,
      });
    } else {
      const folderParent = item.folder_id ?? null;
      const parentId = rootFolderId
        ? folderParent === rootFolderId
          ? null
          : folderParent && apiFolderIds.has(folderParent)
            ? folderParent
            : null
        : folderParent && apiFolderIds.has(folderParent)
          ? folderParent
          : null;
      rows.push({
        id: item.id,
        parentId,
        index: i,
        name: item.name,
        fileType: getMimeLabel(item.mime_type ?? ""),
        size: formatBytes(item.file_size_bytes ?? 0),
        status: resolveStatus(item),
        uploadedAt: new Date(item.created_at).toLocaleDateString(),
        _doc: item,
      });
    }
  });

  return rows;
}

function buildGridData(rows: DocRow[]) {
  const ids: string[] = [];
  const data = new Map<string, DocRow>();
  const meta = new Map<string, DocRowMeta>();

  const sorted = [...rows].sort((a, b) => {
    if (a.parentId === b.parentId) return a.index - b.index;
    return 0;
  });

  for (const row of sorted) {
    data.set(row.id, row);
    const isFolder = !row._doc;
    if (row.parentId === null) {
      ids.push(row.id);
      if (!meta.has(row.id)) {
        meta.set(row.id, isFolder ? { type: "tree", children: [] } : { type: "leaf" });
      }
    } else {
      const parentMeta = meta.get(row.parentId) ?? { type: "tree" as const, children: [] };
      parentMeta.children = [...(parentMeta.children ?? []), row.id];
      meta.set(row.parentId, parentMeta);
      if (!meta.has(row.id)) {
        meta.set(row.id, isFolder ? { type: "tree", children: [] } : { type: "leaf" });
      }
    }
  }

  return { ids, data, meta };
}

// ── Status badge ─────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  PENDING: "#757575",
  PROCESSING: "#1565c0",
  TEXT_EXTRACTION: "#1565c0",
  CHUNKING: "#1565c0",
  EMBEDDING: "#6a1a9a",
  SUMMARIZATION: "#e65100",
  COMPLETED: "#2e7d32",
  FAILED: "#c62828",
};

const STAGE_LABELS: Record<string, string> = {
  TEXT_EXTRACTION: "Extracting",
  CHUNKING: "Chunking",
  EMBEDDING: "Embedding",
  SUMMARIZATION: "Summarizing",
};

function resolveStatus(doc: DocumentItem): string {
  if (doc.status === "PROCESSING") {
    const active = doc.processing_jobs.find((j) => j.status === "IN_PROGRESS");
    if (active) return STAGE_LABELS[active.stage] ?? active.stage;
  }
  return doc.status ?? "PENDING";
}

const Badge = styled.span<{ $status: string }>`
  display: inline-block;
  padding: 2px ${spacing.xsmall}px;
  border-radius: 12px;
  ${text.small};
  font-weight: 600;
  background: ${({ $status }) => STATUS_COLORS[$status] ?? color.textPlaceholder};
  color: ${color.textInverse};
`;

const GridWrapper = styled.div`
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
`;

const LoadMoreWrapper = styled.div`
  padding: ${spacing.xsmall}px ${spacing.medium}px;
  border-top: 1px solid ${color.borderLight};
  display: flex;
  justify-content: center;
`;

// ── Component ─────────────────────────────────────────────────────────────────

interface ItemListProps {
  onSelect: (item: UnifiedItem) => void;
  onChatOpen?: (doc: DocumentItem) => void;
  onFolderOpen?: (folderId: string) => void;
  selectedId?: string;
  filters?: ItemFiltersState;
  parentId?: string;
}

export function ItemList({ onSelect, onChatOpen, onFolderOpen, selectedId, filters, parentId }: ItemListProps) {
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useDocuments(parentId);
  const { mutate: deleteDoc } = useDeleteDocument();
  const { mutate: deleteFolder } = useDeleteFolder();
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [initialised, setInitialised] = useState(false);
  const [folderToBeDeleted, setFolderToBeDeleted] = useState<{ id: string; name: string } | null>(null);
  const [fileToBeDeleted, setFileToBeDeleted] = useState<{ id: string; name: string } | null>(null);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const allItems = useMemo(() => (data?.pages ?? []).flatMap((p) => p.items), [data?.pages]);

  const gridData = useMemo(() => {
    let rows: DocRow[] = unifiedToRows(allItems, parentId);

    if (filters?.statuses.size || filters?.fileTypeIds.size) {
      const allowedMimes = filters.fileTypeIds.size
        ? new Set([...filters.fileTypeIds].flatMap((id) => FILE_TYPE_MIMES[id] ?? []))
        : null;

      const passedChildIds = new Set(
        rows
          .filter((r) => r.parentId !== null && r._doc)
          .filter((r) => {
            const doc = r._doc!;
            if (filters.statuses.size && (!doc.status || !filters.statuses.has(doc.status))) return false;
            if (allowedMimes && (!doc.mime_type || !allowedMimes.has(doc.mime_type))) return false;
            return true;
          })
          .map((r) => r.id),
      );

      const usedParents = new Set(rows.filter((r) => passedChildIds.has(r.id)).map((r) => r.parentId));

      rows = rows.filter((r) => (r.parentId === null && usedParents.has(r.id)) || passedChildIds.has(r.id));
    }

    return buildGridData(rows);
  }, [allItems, filters, parentId]);

  useMemo(() => {
    if (!initialised && gridData.ids.length) {
      const allFolderIds = new Set([...gridData.data.entries()].filter(([, row]) => !row._doc).map(([id]) => id));
      setExpandedRows(allFolderIds);
      setInitialised(true);
    }
  }, [gridData.ids, initialised]);

  const columns = useMemo(
    (): Column<DocRow>[] => [
      {
        id: "name",
        label: "Name",
        tree: true,
        treeIndentSize: "small",
        minWidth: 200,
        width: 400,
        resizable: true,
        cell: {
          Renderer: ({ value, rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row?._doc) {
              return (
                <GridCellBase tabIndex={tabIndex}>
                  <IconWrapper>
                    <Folder />
                    <span
                      style={{ fontWeight: 600, cursor: "pointer", color: color.backgroundPrimary }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onFolderOpen?.(row!.id);
                      }}
                    >
                      {value}
                    </span>
                  </IconWrapper>
                </GridCellBase>
              );
            }
            return (
              <GridCellBase tabIndex={tabIndex}>
                <IconWrapper>
                  {getMimeIcon(row._doc.mime_type ?? "")}
                  <span style={{ color: row.status === "COMPLETED" ? color.backgroundPrimary : "inherit" }}>{value}</span>
                </IconWrapper>
              </GridCellBase>
            );
          },
        },
      },
      {
        id: "fileType",
        label: "Type",
        width: 100,
      },
      {
        id: "size",
        label: "Size",
        width: 110,
      },
      {
        id: "status",
        label: "Status",
        width: 130,
        cell: {
          Renderer: ({ value, tabIndex }) =>
            value ? (
              <GridCellBase tabIndex={tabIndex}>
                <Badge $status={value}>{value}</Badge>
              </GridCellBase>
            ) : (
              <></>
            ),
        },
      },
      {
        id: "uploadedAt",
        label: "Uploaded",
        width: 120,
      },
      {
        id: "chat",
        label: "",
        width: 44,
        cell: {
          Renderer: ({ rowId, tabIndex }) => {
            const row = gridData.data.get(String(rowId));
            if (!row?._doc || row._doc.status !== "COMPLETED") return <></>;
            return (
              <GridCellBase tabIndex={tabIndex}>
                <ButtonAnviEmptyInverse
                  title="Open chat"
                  onClick={(e) => {
                    e.stopPropagation();
                    onChatOpen?.(row._doc!);
                  }}
                  icon={<AiAnvi color="anvi" />}
                ></ButtonAnviEmptyInverse>
              </GridCellBase>
            );
          },
        },
      },
    ],
    [gridData, onChatOpen, onFolderOpen],
  );

  const selection = selectedId ? new Set([selectedId]) : new Set<string>();

  return (
    <GridWrapper>
      <div style={{ flex: 1, minHeight: 0 }}>
        <Grid<DocRow, DocRowMeta>
          label="Documents"
          columns={columns}
          rows={gridData}
          loading={isLoading && !data}
          expandedRows={expandedRows}
          onExpandedRowsChange={setExpandedRows}
          selection={selection}
          selectionMode="single"
          rowHeight="medium"
          onRowClick={(rowId) => {
            const row = gridData.data.get(String(rowId));
            if (!row) return;
            if (row._doc) onSelect(row._doc);
            else if (row._folder) onSelect(row._folder);
          }}
          actionsMenu={({ row }) => (
            <ListItem
              icon={<Trash />}
              label="Delete"
              onActivate={() => {
                if (row._doc) {
                  setFileToBeDeleted({ id: row._doc.id, name: row._doc.name });
                } else {
                  setFolderToBeDeleted({ id: row.id, name: row.name });
                }
                setShowConfirmDelete(true);
              }}
            />
          )}
        />
      </div>
      {hasNextPage && (
        <LoadMoreWrapper>
          <ButtonPrimary onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
            {isFetchingNextPage ? "Loading…" : "Load more"}
          </ButtonPrimary>
        </LoadMoreWrapper>
      )}
      {showConfirmDelete && (!!folderToBeDeleted || !!fileToBeDeleted) ? (
        <Modal
          onConfirm={() => {
            if (fileToBeDeleted) deleteDoc(fileToBeDeleted.id);
            if (folderToBeDeleted) deleteFolder(folderToBeDeleted.id);
            setShowConfirmDelete(false);
          }}
          onCancel={() => setShowConfirmDelete(false)}
          headerText="Confirm Delete"
          confirmText="Delete"
          type={DESTRUCTIVE}
          cancelText="Cancel"
        >
          <p>Are you sure you want to delete this {folderToBeDeleted ? "folder" : "file"}?</p>
        </Modal>
      ) : null}
    </GridWrapper>
  );
}
