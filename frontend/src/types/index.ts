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

export interface Document {
  id: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  summary: string | null;
  created_at: string;
  updated_at: string;
  processing_jobs: ProcessingJob[];
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  offset: number;
  limit: number;
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
  sources?: Array<{
    chunk_id: string;
    document_id: string;
    page_number: number | null;
    score: number;
  }>;
  timestamp: Date;
}
