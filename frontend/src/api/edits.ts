import { apiClient } from "./client";

export interface DocumentEdit {
  id: string;
  document_id: string;
  user_id: string;
  instruction: string;
  original_content: string;
  proposed_content: string;
  status: "pending" | "approved" | "rejected";
  version: number | null;
  created_at: string;
}

export interface EditListResponse {
  edits: DocumentEdit[];
}

export const editsApi = {
  propose: (documentId: string, instruction: string): Promise<DocumentEdit> =>
    apiClient
      .post<DocumentEdit>(`/documents/${documentId}/edits`, { instruction })
      .then((r) => r.data),

  list: (documentId: string): Promise<EditListResponse> =>
    apiClient
      .get<EditListResponse>(`/documents/${documentId}/edits`)
      .then((r) => r.data),

  approve: (documentId: string, editId: string): Promise<DocumentEdit> =>
    apiClient
      .post<DocumentEdit>(`/documents/${documentId}/edits/${editId}/approve`)
      .then((r) => r.data),

  reject: (documentId: string, editId: string): Promise<DocumentEdit> =>
    apiClient
      .post<DocumentEdit>(`/documents/${documentId}/edits/${editId}/reject`)
      .then((r) => r.data),
};
