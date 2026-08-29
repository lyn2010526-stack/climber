import type { JsonObject } from './common';
import type { WorkflowSummary } from './api';

export interface WorkflowNode {
  id: string;
  type?: string | undefined;
  data?: JsonObject;
  position?: { x: number; y: number };
}

export interface WorkflowEdge {
  id?: string;
  source: string;
  target: string;
  condition?: unknown;
}

export interface CreateWorkflowInput {
  name: string;
  description?: string;
  nodes?: WorkflowNode[];
  edges?: WorkflowEdge[];
}

export type UpdateWorkflowInput = Partial<CreateWorkflowInput>;

export interface WorkflowRunResult {
  id: string;
  run_id?: string;
  status: string;
  outputs: JsonObject;
  node_results: JsonObject;
  execution_time_ms: number;
  error: string;
}

export type SavedWorkflow = WorkflowSummary;
