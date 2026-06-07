export type ComplianceStatus = "COMPLIANT" | "WARNING" | "NON_COMPLIANT" | "UNCHECKED" | "SCANNING";
export type RuleType = "keyword_required" | "keyword_forbidden" | "age_limit_days" | "llm_check";
export type Severity = "critical" | "warning";

export interface ComplianceRule {
  id: string;
  name: string;
  description: string | null;
  rule_type: RuleType;
  params: Record<string, unknown>;
  severity: Severity;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ComplianceRuleCreate {
  name: string;
  description?: string;
  rule_type: RuleType;
  params: Record<string, unknown>;
  severity: Severity;
}

export interface ComplianceRuleUpdate {
  name?: string;
  description?: string;
  params?: Record<string, unknown>;
  severity?: Severity;
  is_active?: boolean;
}

export interface Location {
  chunk_index: number | null;
  page_number: number | null;
  excerpt: string;
}

export interface ComplianceRuleResult {
  id: string;
  rule_id: string | null;
  rule_name: string;
  rule_type: RuleType;
  severity: Severity;
  passed: boolean;
  detail: string | null;
  locations: Location[] | null;
}

export interface ComplianceReport {
  id: string;
  document_id: string;
  status: ComplianceStatus;
  checked_at: string;
  is_stale: boolean;
  insights: string | null;
  results: ComplianceRuleResult[];
}

export interface ComplianceStats {
  compliant: number;
  warning: number;
  non_compliant: number;
  unchecked: number;
  total_documents: number;
}

export interface ComplianceIssueFailedRule {
  rule_name: string;
  severity: Severity;
  detail: string | null;
}

export interface ComplianceIssueItem {
  document_id: string;
  document_name: string;
  report_id: string;
  status: ComplianceStatus;
  checked_at: string;
  is_stale: boolean;
  failing_rules: ComplianceIssueFailedRule[];
}

export interface ComplianceIssuesResponse {
  items: ComplianceIssueItem[];
  next_cursor: string | null;
  has_more: boolean;
}
