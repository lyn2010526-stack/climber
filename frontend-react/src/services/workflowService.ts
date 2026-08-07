import { apiClient } from '../lib/api-client';

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  is_template?: boolean;
  run_count?: number;
  last_status?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  result?: unknown;
  error?: string;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  nodes?: WorkflowNode[];
  edges?: WorkflowEdge[];
}

export interface UpdateWorkflowRequest extends Partial<CreateWorkflowRequest> {}

export interface WorkflowValidationResult {
  valid: boolean;
  errors: string[];
}

export const workflowService = {
  async list(): Promise<Workflow[]> {
    return apiClient.get<Workflow[]>('/api/workflows');
  },

  async get(id: string): Promise<Workflow> {
    return apiClient.get<Workflow>(`/api/workflows/${id}`);
  },

  async create(data: CreateWorkflowRequest): Promise<Workflow> {
    return apiClient.post<Workflow>('/api/workflows', data);
  },

  async update(id: string, data: UpdateWorkflowRequest): Promise<Workflow> {
    return apiClient.put<Workflow>(`/api/workflows/${id}`, data);
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete<void>(`/api/workflows/${id}`);
  },

  async execute(workflowId: string, input?: Record<string, unknown>): Promise<WorkflowExecution> {
    return apiClient.post<WorkflowExecution>(`/api/workflows/${workflowId}/execute`, { input: input || {} });
  },

  async stopExecution(workflowId: string, executionId: string): Promise<void> {
    await apiClient.post<void>(
      `/api/workflows/${workflowId}/executions/${executionId}/stop`,
      {}
    );
  },

  async getExecutions(workflowId: string): Promise<WorkflowExecution[]> {
    return apiClient.get<WorkflowExecution[]>(`/api/workflows/${workflowId}/executions`);
  },

  async getExecution(workflowId: string, executionId: string): Promise<WorkflowExecution> {
    return apiClient.get<WorkflowExecution>(`/api/workflows/${workflowId}/executions/${executionId}`);
  },

  async validate(id: string): Promise<WorkflowValidationResult> {
    return apiClient.post<WorkflowValidationResult>(`/api/workflows/${id}/validate`, {});
  },

  async clone(id: string, name?: string): Promise<Workflow> {
    return apiClient.post<Workflow>(`/api/workflows/${id}/clone`, { name });
  },
};