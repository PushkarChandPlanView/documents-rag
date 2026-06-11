import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentsApi } from "@/api/agents";
import type { AgentCreate, AgentUpdate } from "@/types/agent";

const KEY = ["agents"] as const;

export function useAgents() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => agentsApi.list(),
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AgentCreate) => agentsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentUpdate }) =>
      agentsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useAgentRuns(agentId: string | null) {
  return useQuery({
    queryKey: ["agent-runs", agentId],
    queryFn: () => agentsApi.listRuns(agentId!),
    enabled: !!agentId,
  });
}
