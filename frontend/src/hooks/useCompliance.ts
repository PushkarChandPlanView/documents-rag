import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { complianceApi } from "@/api/compliance";
import type { ComplianceRuleCreate, ComplianceRuleUpdate } from "@/types/compliance";

// ── Rules ─────────────────────────────────────────────────────────────────────

export function useComplianceRules() {
  return useQuery({
    queryKey: ["compliance", "rules"],
    queryFn: () => complianceApi.getRules(),
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ComplianceRuleCreate) => complianceApi.createRule(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance", "rules"] });
    },
  });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ComplianceRuleUpdate }) =>
      complianceApi.updateRule(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance", "rules"] });
      // Mark all reports stale (rules changed)
      qc.invalidateQueries({ queryKey: ["compliance", "report"] });
    },
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => complianceApi.deleteRule(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance", "rules"] });
      qc.invalidateQueries({ queryKey: ["compliance", "report"] });
    },
  });
}

// ── Per-document ──────────────────────────────────────────────────────────────

export function useComplianceReport(
  documentId: string | undefined,
  options?: { refetchInterval?: number | false | ((query: { state: { data?: { status?: string } } }) => number | false) }
) {
  return useQuery({
    queryKey: ["compliance", "report", documentId],
    queryFn: () => complianceApi.getReport(documentId!),
    enabled: !!documentId,
    retry: 1,
    refetchInterval: options?.refetchInterval ?? false,
  });
}

export function useTriggerScan(documentId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => complianceApi.triggerScan(documentId!),
    onSuccess: () => {
      // Refetch immediately — backend writes SCANNING to DB before returning 202,
      // so this refetch shows the scanning state without waiting for the poll interval.
      qc.invalidateQueries({ queryKey: ["compliance", "report", documentId] });
      qc.invalidateQueries({ queryKey: ["compliance", "stats"] });
    },
  });
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function useComplianceStats() {
  return useQuery({
    queryKey: ["compliance", "stats"],
    queryFn: () => complianceApi.getStats(),
    refetchInterval: 60_000,
  });
}

export function useComplianceIssues(statusFilter?: string) {
  return useInfiniteQuery({
    queryKey: ["compliance", "issues", statusFilter ?? "all"],
    queryFn: ({ pageParam }) =>
      complianceApi.getIssues({
        cursor: pageParam as string | undefined,
        limit: 50,
        status_filter: statusFilter,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) =>
      lastPage.has_more ? lastPage.next_cursor ?? undefined : undefined,
  });
}
