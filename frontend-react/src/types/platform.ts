import type { JsonObject, OkResult } from './common';

export interface ApiKeyRecord {
  id: string;
  provider: string;
  name: string;
  base_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CreateApiKeyInput {
  provider: string;
  name: string;
  api_key: string;
  base_url?: string | null;
}

export interface FeedbackResult extends OkResult {
  id: string;
}

export interface FeedbackStats {
  total: number;
  approval_rate: number;
  up_count: number;
  down_count: number;
  reason_distribution: Record<string, number>;
}

export interface ReasoningFeedbackInput {
  rating: number;
  thumbs?: string;
  comment?: string;
}

export interface ReasoningFeedbackResult {
  status?: string;
  message?: string;
  ok?: boolean;
  id?: string;
}

export interface ReasoningCandidate {
  id: string;
  strategy: string;
  path_type: string;
  content: string;
  confidence: number;
  metadata: JsonObject;
}

export interface ReasoningPathTrace {
  candidate_id: string;
  path_type: string;
  rounds: Array<{ round_num: number; action: string; output_summary: string }>;
  final_confidence: number;
}

export interface ReasoningCoverage {
  score: number;
  edge_cases: Array<{ description: string; category: string; tested: boolean; result: string }>;
  risks: Array<{ description: string; probability: string; impact: string; mitigation: string }>;
  assumptions: Array<{ statement: string; validated: boolean; evidence: string; risk_if_wrong: string }>;
  blind_spots: string[];
  checklist: Record<string, boolean>;
}

export interface ReasoningResult {
  answer: string;
  mode_used: string;
  candidates: ReasoningCandidate[];
  coverage: ReasoningCoverage | null;
  total_duration_ms: number;
  trace: {
    trace_id: string;
    path_traces: ReasoningPathTrace[];
    coverage_checks: unknown[];
    final_selection_reason: string;
  } | null;
}

export interface ReasoningHistoryItem {
  trace_id: string | null;
  task: string;
  mode: string;
  candidates: number;
  best_confidence: number;
  coverage_score: number | null;
  duration_ms: number;
  created_at: string | null;
}

export interface CostUsage {
  total_cost: number;
  total_tokens: number;
  total_calls: number;
  by_model: Array<{ model: string; cost: number; tokens: number; calls: number }>;
  by_day: Array<{ date: string; cost: number; tokens: number }>;
}

export interface CostBudget {
  amount: number;
  period: string;
  is_active: boolean;
  per_session_limit: number | null;
  per_request_limit: number | null;
}

export interface CostQuota {
  max_requests_per_day: number;
  max_tokens_per_day: number;
  max_cost_per_month: number;
  requests_today: number;
  tokens_today: number;
  cost_this_month: number;
}

export interface SchedulerTask {
  id: string;
  name: string;
  description: string;
  cron: string;
  type?: string;
  enabled: boolean;
  last_run: number | null;
  next_run: number | null;
  run_count: number;
}

export interface CreateSchedulerTaskInput {
  name: string;
  description?: string;
  cron: string;
  task_type?: string;
  nodes?: unknown[];
  edges?: unknown[];
}

export type UpdateSchedulerTaskInput = Partial<CreateSchedulerTaskInput & { enabled: boolean; schedule: string }>;

export interface DeletedResourceResult extends OkResult {
  deleted?: string;
}

export interface EvalDataset {
  id: string;
  name: string;
  description: string;
  case_count: number;
  created_at: string;
}

export interface EvalRun {
  id: string;
  dataset_id: string;
  agent_id: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  average_score: number;
  created_at: string;
}

export interface SeedDatasetsResult extends OkResult {
  created: number;
  datasets: EvalDataset[];
}

export interface SearchResult {
  id: string;
  document_id: string;
  content: string;
  chunk_index: number;
  score: number;
  created_at: string;
}

export interface DoctorCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface DoctorSection {
  section: string;
  checks: DoctorCheck[];
}

export interface DoctorReport {
  version: string;
  platform: { system: string; python: string };
  sections: DoctorSection[];
  healthy: boolean;
}

export interface CommandResult {
  output: string;
  ok: boolean;
}
