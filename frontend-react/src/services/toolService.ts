import { apiClient } from '../lib/api-client';

export interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  config?: Record<string, unknown>;
  schema?: Record<string, unknown>;
}

export interface ToolExecutionRequest {
  tool_id: string;
  arguments: Record<string, unknown>;
  session_id?: string;
}

export interface ToolExecutionResult {
  id: string;
  tool_id: string;
  status: 'success' | 'error' | 'timeout';
  result?: unknown;
  error?: string;
  duration_ms?: number;
}

export const toolService = {
  async list(): Promise<Tool[]> {
    return apiClient.get<Tool[]>('/api/tools');
  },

  async get(id: string): Promise<Tool> {
    return apiClient.get<Tool>(`/api/tools/${id}`);
  },

  async execute(data: ToolExecutionRequest): Promise<ToolExecutionResult> {
    return apiClient.post<ToolExecutionResult>('/api/tools/execute', data);
  },

  async toggle(id: string, enabled: boolean): Promise<Tool> {
    return apiClient.patch<Tool>(`/api/tools/${id}`, { enabled });
  },

  async getConfig(id: string): Promise<Record<string, unknown>> {
    return apiClient.get<Record<string, unknown>>(`/api/tools/${id}/config`);
  },

  async updateConfig(id: string, config: Record<string, unknown>): Promise<Tool> {
    return apiClient.put<Tool>(`/api/tools/${id}/config`, config);
  },
};