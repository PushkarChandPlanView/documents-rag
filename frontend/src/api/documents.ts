import { apiClient } from "./client";
import type { Document, DocumentListResponse, UploadResponse } from "@/types";

export const documentsApi = {
  list: async (offset = 0, limit = 50): Promise<DocumentListResponse> => {
    const res = await apiClient.get<DocumentListResponse>("/documents", {
      params: { offset, limit },
    });
    return res.data;
  },

  get: async (id: string): Promise<Document> => {
    const res = await apiClient.get<Document>(`/documents/${id}`);
    return res.data;
  },

  upload: async (
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<UploadResponse>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
      timeout: 300_000, // 5 min for large files
    });
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/documents/${id}`);
  },
};
