export type OutputFormat = "markdown" | "text" | "json" | "planview";

export type AgentTool =
  | "search_all"
  | "search_jira"
  | "search_confluence"
  | "search_slack"
  | "search_github"
  | "search_hubspot";

export interface Agent {
  id: string;
  name: string;
  description?: string;
  system_prompt: string;
  output_format: OutputFormat;
  tools: AgentTool[];
  max_iter: number;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  description?: string;
  system_prompt: string;
  output_format: OutputFormat;
  tools: AgentTool[];
  max_iter: number;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  system_prompt?: string;
  output_format?: OutputFormat;
  tools?: AgentTool[];
  max_iter?: number;
}

export type RunStatus = "running" | "completed" | "failed";

export interface AgentRun {
  id: string;
  agent_id: string;
  user_id: string;
  query: string;
  status: RunStatus;
  plan: string[] | null;
  result_document_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface PlanviewResult {
  board_id: number | null;
  board_name: string;
  activities: number;
  total_cards: number;
  errors: string[];
}

// SSE event shapes streamed from POST /agents/{id}/run
export type RunEvent =
  | { type: "plan"; steps: string[] }
  | { type: "step_done"; step: number; step_text?: string; source_types?: string[] | null; chunks_found?: number }
  | { type: "generating" }
  | { type: "token"; content: string }
  | { type: "uploaded"; document_id: string }
  | { type: "planview_done"; board_id: number; board_name: string; activities: number; total_cards: number; errors: string[] }
  | { type: "done"; document_id?: string; planview_result?: PlanviewResult }
  | { type: "error"; content: string };
