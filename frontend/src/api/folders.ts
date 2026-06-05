import { apiClient } from "./client";
import type { Folder, FolderItem, FolderListResponse } from "@/types";

export const foldersApi = {
  list: async (parentId?: string): Promise<FolderListResponse> => {
    const res = await apiClient.get<FolderListResponse>("/folders", {
      params: parentId ? { parent_id: parentId } : {},
    });
    return res.data;
  },

  get: async (id: string): Promise<FolderItem> => {
    const res = await apiClient.get<FolderItem>(`/folders/${id}`);
    return res.data;
  },

  breadcrumb: async (id: string): Promise<FolderItem[]> => {
    const res = await apiClient.get<{ items: FolderItem[] }>(`/folders/${id}/breadcrumb`);
    return res.data.items;
  },

  create: async (name: string, parentId?: string): Promise<Folder> => {
    const res = await apiClient.post<Folder>("/folders", {
      name,
      parent_id: parentId ?? null,
    });
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/folders/${id}`);
  },
};
