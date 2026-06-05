import { apiClient } from "./client";
import type { Document, UnifiedListResponse, UploadResponse } from "@/types";

export const documentsApi = {
  list: async (cursor?: string | null, limit = 50, parentId?: string): Promise<UnifiedListResponse> => {
    const res = await apiClient.get<UnifiedListResponse>("/documents", {
      params: {
        limit,
        ...(cursor ? { cursor } : {}),
        ...(parentId ? { parent_id: parentId } : {}),
      },
    });
    return res.data;
  },

  get: async (id: string): Promise<Document> => {
    const res = await apiClient.get<Document>(`/documents/${id}`);
    return res.data;
  },

  upload: async (
    file: File,
    onProgress?: (percent: number) => void,
    folderId?: string,
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    if (folderId) formData.append("folder_id", folderId);
    const res = await apiClient.post<UploadResponse>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
      timeout: 300_000,
    });
    return res.data;
  },

  addLink: async (url: string, title?: string, folderId?: string): Promise<UploadResponse> => {
    const res = await apiClient.post<UploadResponse>("/documents/link", {
      url,
      title: title || null,
      folder_id: folderId ?? null,
    });
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/documents/${id}`);
  },

  deleteFolder: async (id: string): Promise<void> => {
    await apiClient.delete(`/folders/${id}`);
  },

  updateDocument: async (id: string, data: { name?: string; description?: string | null; parent_id?: string | null }): Promise<void> => {
    await apiClient.patch(`/documents/${id}`, data);
  },

  updateFolder: async (id: string, data: { name?: string; description?: string | null; parent_id?: string | null }): Promise<void> => {
    await apiClient.patch(`/folders/${id}`, data);
  },
};
