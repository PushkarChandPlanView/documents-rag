import { apiClient } from "./client";
import type {
  ComplianceIssuesResponse,
  ComplianceReport,
  ComplianceRule,
  ComplianceRuleCreate,
  ComplianceRuleUpdate,
  ComplianceStats,
} from "@/types/compliance";

export const complianceApi = {
  // Rules
  getRules: () =>
    apiClient.get<ComplianceRule[]>("/compliance/rules").then((r) => r.data),

  createRule: (data: ComplianceRuleCreate) =>
    apiClient.post<ComplianceRule>("/compliance/rules", data).then((r) => r.data),

  updateRule: (id: string, data: ComplianceRuleUpdate) =>
    apiClient.patch<ComplianceRule>(`/compliance/rules/${id}`, data).then((r) => r.data),

  deleteRule: (id: string) => apiClient.delete(`/compliance/rules/${id}`),

  // Per-document
  getReport: (documentId: string) =>
    apiClient.get<ComplianceReport>(`/compliance/documents/${documentId}`).then((r) => r.data),

  triggerScan: (documentId: string) =>
    apiClient.post(`/compliance/documents/${documentId}/scan`).then((r) => r.data),

  // Dashboard
  getStats: () =>
    apiClient.get<ComplianceStats>("/compliance/stats").then((r) => r.data),

  getIssues: (params?: { cursor?: string; limit?: number; status_filter?: string }) =>
    apiClient
      .get<ComplianceIssuesResponse>("/compliance/issues", { params })
      .then((r) => r.data),
};
