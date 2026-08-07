import { apiClient } from '../lib/api-client';

export interface McpServer {
  id: string;
  name: string;
  url: string;
  status: 'connected' | 'disconnected' | 'error';
  tools?: McpTool[];
  last_connected?: string;
}

export interface McpTool {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface McpServerConfig {
  name: string;
  url: string;
  headers?: Record<string, string>;
  timeout?: number;
}

export interface McpStatus {
  status: string;
  ready: boolean;
  servers: number;
}

export const mcpService = {
  async listServers(): Promise<McpServer[]> {
    return apiClient.get<McpServer[]>('/api/mcp/servers');
  },

  async getServer(id: string): Promise<McpServer> {
    return apiClient.get<McpServer>(`/api/mcp/servers/${id}`);
  },

  async addServer(data: McpServerConfig): Promise<McpServer> {
    return apiClient.post<McpServer>('/api/mcp/servers', data);
  },

  async updateServer(id: string, data: Partial<McpServerConfig>): Promise<McpServer> {
    return apiClient.put<McpServer>(`/api/mcp/servers/${id}`, data);
  },

  async removeServer(id: string): Promise<void> {
    await apiClient.delete<void>(`/api/mcp/servers/${id}`);
  },

  async connect(id: string): Promise<McpServer> {
    return apiClient.post<McpServer>(`/api/mcp/servers/${id}/connect`, {});
  },

  async disconnect(id: string): Promise<McpServer> {
    return apiClient.post<McpServer>(`/api/mcp/servers/${id}/disconnect`, {});
  },

  async listTools(serverId: string): Promise<McpTool[]> {
    return apiClient.get<McpTool[]>(`/api/mcp/servers/${serverId}/tools`);
  },

  async callTool(serverId: string, toolName: string, args: Record<string, unknown>): Promise<unknown> {
    return apiClient.post<unknown>(`/api/mcp/servers/${serverId}/tools/${toolName}`, args);
  },

  async getStatus(): Promise<McpStatus> {
    return apiClient.get<McpStatus>('/api/mcp/status');
  },
};