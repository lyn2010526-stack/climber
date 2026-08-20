// Catalog resources: tools, models, skills, documents and MCP servers.
import type { DocumentSummary, ModelSummary, SkillSummary, ToolSummary } from '../types/api';
import { ApiClient, BASE_URL } from './client';

declare module './client' {
  interface ApiClient {
    listTools(): Promise<ToolSummary[]>;
    listModels(): Promise<ModelSummary[]>;
    listDocuments(): Promise<DocumentSummary[]>;
    listSkills(): Promise<SkillSummary[]>;
    updateSkill(id: string, data: any): Promise<any>;
    runAutonomousSkillStream(
      goal: string,
      skills: string[],
      promptTemplate: string,
      onEvent: (event: { type: string; data?: any }) => void,
    ): () => void;
    listMCPServers(): Promise<any[]>;
    listMCPCategories(): Promise<any[]>;
    installMCPServer(id: string, config?: Record<string, any>): Promise<any>;
    deleteMCPServer(id: string): Promise<any>;
  }
}

ApiClient.prototype.listTools = function (this: ApiClient): Promise<ToolSummary[]> {
  return this.request<ToolSummary[]>('/tools');
};

ApiClient.prototype.listModels = function (this: ApiClient): Promise<ModelSummary[]> {
  return this.request<ModelSummary[]>('/models');
};

ApiClient.prototype.listDocuments = function (this: ApiClient): Promise<DocumentSummary[]> {
  return this.request<DocumentSummary[]>('/documents/');
};

ApiClient.prototype.listSkills = function (this: ApiClient): Promise<SkillSummary[]> {
  return this.request<SkillSummary[]>('/skills');
};

ApiClient.prototype.updateSkill = function (this: ApiClient, id: string, data: any) {
  return this.request<any>(`/skills/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.runAutonomousSkillStream = function (
  this: ApiClient,
  goal: string,
  skills: string[],
  promptTemplate: string,
  onEvent: (event: { type: string; data?: any }) => void,
): () => void {
  const url = `${BASE_URL}/skills/autonomous/run`;
  const abortController = new AbortController();

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
    body: JSON.stringify({ goal, skills, prompt_template: promptTemplate }),
    signal: abortController.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        onEvent({ type: 'done' });
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6);
        if (data === '[DONE]') {
          onEvent({ type: 'done' });
          return;
        }

        try {
          const event = JSON.parse(data);
          onEvent(event);
        } catch { /* skip */ }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onEvent({ type: 'error', data: { detail: err.message } });
    }
  });

  return () => abortController.abort();
};

ApiClient.prototype.listMCPServers = function (this: ApiClient) {
  return this.request<any[]>('/mcp/servers');
};

ApiClient.prototype.listMCPCategories = function (this: ApiClient) {
  return this.request<any[]>('/mcp/categories');
};

ApiClient.prototype.installMCPServer = function (this: ApiClient, id: string, config?: Record<string, any>) {
  return this.request<any>(`/mcp/servers/${id}/install`, {
    method: 'POST',
    body: JSON.stringify(config || {}),
  });
};

ApiClient.prototype.deleteMCPServer = function (this: ApiClient, id: string) {
  return this.request(`/mcp/servers/${id}`, { method: 'DELETE' });
};
