import { useAuthStore } from "@/store/authStore";
import type {
  Agent,
  AgentCreate,
  AgentUpdate,
  AgentRun,
  RunEvent,
} from "@/types/agent";

const AGENT_API = "/agent-ui/api";

async function agentFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const token = useAuthStore.getState().accessToken;
  const res = await fetch(`${AGENT_API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text);
  }
  return res.json() as Promise<T>;
}

export const agentsApi = {
  list: () => agentFetch<Agent[]>("/agents"),

  get: (id: string) => agentFetch<Agent>(`/agents/${id}`),

  create: (data: AgentCreate) =>
    agentFetch<Agent>("/agents", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: AgentUpdate) =>
    agentFetch<Agent>(`/agents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    agentFetch<void>(`/agents/${id}`, { method: "DELETE" }),

  getRun: (runId: string) => agentFetch<AgentRun>(`/runs/${runId}`),

  listRuns: (agentId: string) =>
    agentFetch<AgentRun[]>(`/agents/${agentId}/runs`),

  /** Opens an SSE stream for a run. Caller receives parsed RunEvent objects. */
  streamRun: async function* (
    agentId: string,
    query: string,
    userId: string,
    signal?: AbortSignal
  ): AsyncGenerator<RunEvent> {
    const token = useAuthStore.getState().accessToken;
    const res = await fetch(`${AGENT_API}/agents/${agentId}/run`, {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ query, user_id: userId }),
    });

    if (!res.ok || !res.body) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(text);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const json = line.slice(6).trim();
        if (!json || json === "[DONE]") continue;
        try {
          yield JSON.parse(json) as RunEvent;
        } catch {
          // malformed SSE line — skip
        }
      }
    }
  },
};
