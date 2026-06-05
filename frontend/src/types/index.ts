export interface User {
  id: string;
  email: string;
  is_active: boolean;
}

export interface ProcessingJob {
  id: string;
  stage: "TEXT_EXTRACTION" | "CHUNKING" | "EMBEDDING" | "SUMMARIZATION";
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED";
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

// ── Unified list items (from GET /documents) ──────────────────────────────────

export interface FolderItem {
  type: "folder";
  id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  type: "document";
  id: string;
  filename: string;        // mapped from items.name
  description: string | null;
  mime_type: string;
  file_size_bytes: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  folder_id: string | null;
  folder_name: string | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
  processing_jobs: ProcessingJob[];
}

export type UnifiedItem = FolderItem | DocumentItem;

export interface UnifiedListResponse {
  items: UnifiedItem[];
  next_cursor: string | null;
  has_more: boolean;
}

// ── Single-document detail (from GET /documents/:id) ─────────────────────────

export interface DocumentDetailResponse {
  type: "document";
  id: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  folder_id: string | null;
  folder_name: string | null;
  source_url: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
  processing_jobs: ProcessingJob[];
}

// ── Legacy alias (kept for backward compat in non-refactored components) ──────
export type Document = DocumentDetailResponse;

// ── Other response types ──────────────────────────────────────────────────────

export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface FolderListResponse {
  items: Folder[];
  total: number;
}

export interface UploadResponse {
  document_id: string;
  status: string;
  status_ws_url: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  text: string;
  score: number;
  page_number: number | null;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: string;
  sources?: Array<{
    chunk_id: string;
    document_id: string;
    page_number: number | null;
    score: number;
  }>;
  timestamp: Date;
}
