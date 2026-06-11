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
    _documentIds?: string[],
    topK = 10
  ): Promise<DocumentSearchResponse> => {
    const { userEmail } = useAuthStore.getState();
    const res = await fetch("/search-ui/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        user_id: userEmail ?? "admin@example.com",
        top_k: topK,
        mode: "hybrid",
        source_types: null,
      }),
    });
    if (!res.ok) throw new Error("Document search failed");
    const raw = await res.json() as {
      query: string;
      results: Array<{
        document_id: string;
        document_name: string;
        file_type: string;
        source_type: string;
        score: number;
        text: string;
        page_number: number | null;
      }>;
    };
    return {
      query: raw.query,
      results: raw.results.map((r) => ({
        document_id: r.document_id,
        document_name: r.document_name,
        file_type: r.file_type,
        score: r.score,
        snippet: r.text,
        page_number: r.page_number,
        source_type: r.source_type,
        created_at: "",
        updated_at: "",
        status: null,
        description: null,
        file_size_bytes: null,
      })),
    };
  },
};
