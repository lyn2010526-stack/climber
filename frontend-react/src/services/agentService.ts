import { apiClient } from '../lib/api-client';

export interface Agent {
  id: string;
  name: string;
  provider: string;
  model_id: string;
  description?: string;
  system_prompt?: string;
  tools?: string[];
  skills?: string[];
  status: 'idle' | 'running' | 'paused' | 'error';
  created_at: string;
  updated_at: string;
}

export interface CreateAgentRequest {
  name: string;
  provider: string;
  model_id: string;
  description?: string;
  system_prompt?: string;
  tools?: string[];
  skills?: string[];
}

export interface UpdateAgentRequest extends Partial<CreateAgentRequest> {}

export interface AgentExecution {
  id: string;
  agent_id: string;
  session_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  input?: string;
  output?: string;
  started_at: string;
  completed_at?: string;
  error?: string;
}

export const agentService = {
  async list(): Promise<Agent[]> {
    return apiClient.get<Agent[]>('/api/agents');
  },

  async get(id: string): Promise<Agent> {
    return apiClient.get<Agent>(`/api/agents/${id}`);
  },

  async create(data: CreateAgentRequest): Promise<Agent> {
    return apiClient.post<Agent>('/api/agents', data);
  },

  async update(id: string, data: UpdateAgentRequest): Promise<Agent> {
    return apiClient.put<Agent>(`/api/agents/${id}`, data);
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete<void>(`/api/agents/${id}`);
  },

  async execute(agentId: string, input: string, sessionId?: string): Promise<AgentExecution> {
    return apiClient.post<AgentExecution>(`/api/agents/${agentId}/execute`, {
      input,
      session_id: sessionId,
    });
  },

  async stopExecution(agentId: string, executionId: string): Promise<void> {
    await apiClient.post<void>(`/api/agents/${agentId}/executions/${executionId}/stop`, {});
  },

  async getExecutions(agentId: string): Promise<AgentExecution[]> {
    return apiClient.get<AgentExecution[]>(`/api/agents/${agentId}/executions`);
  },

  async getExecution(agentId: string, executionId: string): Promise<AgentExecution> {
    return apiClient.get<AgentExecution>(`/api/agents/${agentId}/executions/${executionId}`);
  },

  async clone(id: string, name?: string): Promise<Agent> {
    return apiClient.post<Agent>(`/api/agents/${id}/clone`, { name });
  },
};