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
  sourceHandle?: string | null;
  targetHandle?: string | null;
}

export interface WorkflowNodePort {
  id: string;
  label: string;
  data_type: string;
  required: boolean;
}

export interface WorkflowNodeTypeDefinition {
  type: string;
  label: string;
  description: string;
  category: string;
  color: string;
  inputs: WorkflowNodePort[];
  outputs: WorkflowNodePort[];
  runtime_type?: string | null;
  builtin: boolean;
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

export interface WorkflowNodeRunResult {
  node_id: string;
  status: string;
  output: unknown;
  execution_time_ms: number;
  error: string;
}

export type SavedWorkflow = WorkflowSummary;
