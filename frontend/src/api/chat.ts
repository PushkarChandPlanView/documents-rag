import { useAuthStore } from "@/store/authStore";
import type { DocumentSearchResponse } from "@/types";

const API_URL = import.meta.env.VITE_API_URL || "/api";

export interface ChatStreamEvent {
  type?: "status" | "token";
  message?: string;
  token: string;
  sources: Array<{
    chunk_id: string;
    document_id: string;
    page_number: number | null;
    score: number;
  }>;
  done: boolean;
}

export async function* streamChat(
  query: string,
  documentIds?: string[],
  conversationId?: string
): AsyncGenerator<ChatStreamEvent> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      query,
      document_ids: documentIds ?? null,
      conversation_id: conversationId ?? null,
    }),
  });

  if (!res.ok) throw new Error(`Chat API error: ${res.status}`);

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6)) as ChatStreamEvent;
          yield event;
          if (event.done) return;
        } catch {
          // ignore malformed SSE lines
        }
      }
    }
  }
}

export const searchApi = {
  search: async (query: string, documentIds?: string[], topK = 5) => {
    const token = useAuthStore.getState().accessToken;
    const res = await fetch(`${API_URL}/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, document_ids: documentIds, top_k: topK }),
    });
    if (!res.ok) throw new Error("Search failed");
    return res.json();
  },

  searchDocuments: async (
    query: string,
    documentIds?: string[],
    topK = 10
  ): Promise<DocumentSearchResponse> => {
    const token = useAuthStore.getState().accessToken;
    const res = await fetch(`${API_URL}/search/documents`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query, document_ids: documentIds ?? null, top_k: topK }),
    });
    if (!res.ok) throw new Error("Document search failed");
    return res.json();
  },
};
