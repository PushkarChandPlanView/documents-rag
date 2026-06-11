import type {
  CommentCreate,
  CommentItem,
  CommentUpdate,
  PaginatedComments,
} from "@/types/comments";
import { apiClient } from "./client";

const BASE = "/v1";

export const commentsApi = {
  list: (documentId: string, page = 1, pageSize = 20): Promise<PaginatedComments> =>
    apiClient.get<PaginatedComments>(`${BASE}/documents/${documentId}/comments`, {
      params: { page, page_size: pageSize },
    }).then((r) => r.data),

  create: (payload: CommentCreate): Promise<CommentItem> =>
    apiClient.post<CommentItem>(`${BASE}/comments`, payload).then((r) => r.data),

  update: (commentId: string, payload: CommentUpdate): Promise<CommentItem> =>
    apiClient.put<CommentItem>(`${BASE}/comments/${commentId}`, payload).then((r) => r.data),

  remove: (commentId: string): Promise<void> =>
    apiClient.delete(`${BASE}/comments/${commentId}`).then(() => undefined),

  like: (commentId: string): Promise<void> =>
    apiClient.post(`${BASE}/comments/${commentId}/like`).then(() => undefined),

  unlike: (commentId: string): Promise<void> =>
    apiClient.delete(`${BASE}/comments/${commentId}/like`).then(() => undefined),
};
