// Agents resource domain.
import type { AgentSummary } from '../types/api';
import { ApiClient } from './client';

declare module './client' {
  interface ApiClient {
    listAgents(): Promise<AgentSummary[]>;
    createAgent(data: any): Promise<any>;
    deleteAgent(id: string): Promise<any>;
  }
}

ApiClient.prototype.listAgents = async function (this: ApiClient): Promise<AgentSummary[]> {
  const response = await this.request<AgentSummary[] | { items: AgentSummary[] }>('/agents');
  return Array.isArray(response) ? response : response.items;
};

ApiClient.prototype.createAgent = function (this: ApiClient, data: any) {
  return this.request<any>('/agents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.deleteAgent = function (this: ApiClient, id: string) {
  return this.request(`/agents/${id}`, { method: 'DELETE' });
};
