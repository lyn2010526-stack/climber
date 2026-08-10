// API client for backend communication

const BASE_URL = '/api/v1';

export interface ApiError {
  detail: string;
}

class ApiClient {
  private getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...options.headers as Record<string, string>,
    };

    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Agents
  async listAgents() {
    const response = await this.request<any[] | { items: any[] }>('/agents');
    return Array.isArray(response) ? response : response.items;
  }

  async createAgent(data: any) {
    return this.request<any>('/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteAgent(id: string) {
    return this.request(`/agents/${id}`, { method: 'DELETE' });
  }

  // Sessions
  async listSessions() {
    const response = await this.request<any[] | { items: any[] }>('/sessions');
    return Array.isArray(response) ? response : response.items;
  }

  async createSession(data: any) {
    return this.request<any>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteSession(id: string) {
    return this.request(`/sessions/${id}`, { method: 'DELETE' });
  }

  async getSessionMessages(sessionId: string) {
    return this.request<any>(`/sessions/${sessionId}/messages`);
  }

  // Chat (SSE)
  chatStream(sessionId: string, message: string, onEvent: (event: { event: string; data: any }) => void): () => void {
    const url = `${BASE_URL}/sessions/${sessionId}/chat`;
    const abortController = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
      body: JSON.stringify({ message }),
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
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const eventBlock of events) {
          const lines = eventBlock.split('\n');
          let eventName = '';
          let dataStr = '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('event:')) {
              eventName = trimmed.slice(6).trim();
            } else if (trimmed.startsWith('data:')) {
              dataStr += trimmed.slice(5).trim();
            }
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            onEvent({ event: eventName || 'text', data });
          } catch {
            onEvent({ event: eventName || 'text', data: dataStr });
          }
        }
      }
    }).catch((err) => {
      if (err.name !== 'AbortError') {
        onEvent({ event: 'error', data: JSON.stringify({ detail: err.message }) });
      }
    });

    return () => abortController.abort();
  }

  // Tools
  async listTools() {
    return this.request<any[]>('/tools');
  }

  // Models
  async listModels() {
    return this.request<any[]>('/models');
  }

  // Workflows
  async listWorkflows() {
    return this.request<any[]>('/workflows/');
  }

  async listWorkflowTemplates() {
    return this.request<any[]>('/workflows/templates');
  }

  async createWorkflowFromTemplate(templateId: string) {
    return this.request<any>(`/workflows/templates/${templateId}`, {
      method: 'POST',
    });
  }

  async createWorkflow(data: any) {
    return this.request<any>('/workflows/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateWorkflow(id: string, data: any) {
    return this.request<any>(`/workflows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async runWorkflow(id: string, inputs?: Record<string, string>) {
    return this.request<any>(`/workflows/${id}/run`, {
      method: 'POST',
      body: JSON.stringify(inputs || {}),
    });
  }

  // API Keys
  async listApiKeys() {
    return this.request<any[]>('/api-keys');
  }

  async addApiKey(data: any) {
    return this.request<any>('/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteApiKey(id: string) {
    return this.request(`/api-keys/${id}`, { method: 'DELETE' });
  }

  // Stats
  async getStats() {
    return this.request<any>('/stats');
  }
  // Cluster / Groups
  async createCluster(requirements: string) {
    return this.request<any>('/cluster/create', {
      method: 'POST',
      body: JSON.stringify({ requirements }),
    });
  }

  async getClusterStatus() {
    return this.request<any>('/cluster/status');
  }

  async listGroups() {
    return this.request<any[]>('/groups/');
  }

  async createGroup(data: { name: string; description?: string; topic?: string }) {
    return this.request<any>('/groups/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getGroup(id: string) {
    return this.request<any>(`/groups/${id}`);
  }

  async addGroupMember(groupId: string, data: Record<string, any>) {
    return this.request<any>(`/groups/${groupId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async removeGroupMember(groupId: string, memberId: string) {
    return this.request<any>(`/groups/${groupId}/members/${memberId}`, { method: 'DELETE' });
  }

  async listGroupMessages(groupId: string, limit = 50) {
    return this.request<any>(`/groups/${groupId}/messages?limit=${limit}`);
  }

  // Documents
  async listDocuments() {
    return this.request<any[]>('/documents/');
  }

  // Traces
  async listTraces() {
    return this.request<any>('/traces/');
  }

  // Plugins
  async listPlugins(type?: string, status?: string) {
    const params = new URLSearchParams();
    if (type) params.set('type', type);
    if (status) params.set('status', status);
    const qs = params.toString();
    return this.request<any[]>(`/plugins${qs ? '?' + qs : ''}`);
  }

  async getMarketplace() {
    return this.request<any>('/plugins/marketplace');
  }

  async installPlugin(id: string, config?: Record<string, any>) {
    return this.request<any>(`/plugins/${id}/install`, {
      method: 'POST',
      body: JSON.stringify(config || {}),
    });
  }

  async uninstallPlugin(id: string) {
    return this.request<any>(`/plugins/${id}/uninstall`, { method: 'POST' });
  }

  async enablePlugin(id: string) {
    return this.request<any>(`/plugins/${id}/enable`, { method: 'POST' });
  }

  async disablePlugin(id: string) {
    return this.request<any>(`/plugins/${id}/disable`, { method: 'POST' });
  }

  async importPlugin(sourceUrl: string, name?: string, type?: string) {
    return this.request<any>('/plugins/import', {
      method: 'POST',
      body: JSON.stringify({ source_url: sourceUrl, name: name || '', type: type || 'mcp' }),
    });
  }

  async listSkills() {
    return this.request<any[]>('/skills');
  }

  async sendNotification(title: string, message: string) {
    return this.request<any>('/notifications/send', {
      method: 'POST',
      body: JSON.stringify({ title, message }),
    });
  }

  async testNotification() {
    return this.request<any>('/notifications/test');
  }

  async runDoctor() {
    return this.request<any>('/doctor');
  }

  // Reasoning
  async listReasoningModes() {
    return this.request<any[]>('/reason/modes');
  }

  async reasonStream(
    task: string,
    mode: string,
    maxPaths: number,
    maxRefineRounds: number,
    coverageEnabled: boolean,
    _onEvent: (event: any) => void,
  ): Promise<any> {
    const body = { task, mode, max_paths: maxPaths, max_refine_rounds: maxRefineRounds, coverage_enabled: coverageEnabled };

    return this.request<any>('/reason', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // Feedback
  async submitFeedback(messageId: string, rating: string, reason?: string) {
    const params = new URLSearchParams({ message_id: messageId, rating });
    if (reason) params.set('reason', reason);
    return this.request<any>(`/feedback?${params.toString()}`, { method: 'POST' });
  }

  async getFeedbackStats() {
    return this.request<{
      total: number;
      approval_rate: number;
      up_count: number;
      down_count: number;
      reason_distribution: Record<string, number>;
    }>('/feedback/stats');
  }

  async submitReasoningFeedback(traceId: string, data: { rating: number; thumbs?: string; comment?: string }) {
    return this.request<any>(`/reason/${traceId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listReasoningHistory(limit = 50) {
    return this.request<any[]>(`/reason/history?limit=${limit}`);
  }

  // Settings
  async getSettings() {
    return this.request<any>('/settings/');
  }

  async updateSettings(data: Record<string, any>) {
    return this.request<any>('/settings/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Tasks
  async listTasks(params?: { status?: string; limit?: number }) {
    const qs = params ? '?' + new URLSearchParams(params as any).toString() : '';
    return this.request<any[]>(`/tasks${qs}`);
  }

  async getTask(taskId: string) {
    return this.request<any>(`/tasks/${taskId}`);
  }

  async createTask(data: any) {
    return this.request<any>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async runTask(id: string, inputs?: Record<string, any>) {
    return this.request<any>(`/tasks/${id}/run`, {
      method: 'POST',
      body: JSON.stringify(inputs || {}),
    });
  }

  async cancelTask(id: string) {
    return this.request<any>(`/tasks/${id}/cancel`, { method: 'POST' });
  }

  async pauseTask(id: string) {
    return this.request<any>(`/tasks/${id}/pause`, { method: 'POST' });
  }

  async resumeTask(id: string) {
    return this.request<any>(`/tasks/${id}/resume`, { method: 'POST' });
  }

  async stopTask(id: string) {
    return this.request<any>(`/tasks/${id}/stop`, { method: 'POST' });
  }

  // Cost
  async getCostUsage() {
    return this.request<any>('/cost/usage');
  }

  async getCostBudget() {
    return this.request<any>('/cost/budget');
  }

  // Scheduler
  async listSchedulerTasks() {
    return this.request<any[]>('/scheduler/tasks');
  }

  async createSchedulerTask(data: any) {
    return this.request<any>('/scheduler/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSchedulerTask(id: string, data: any) {
    return this.request<any>(`/scheduler/tasks/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteSchedulerTask(id: string) {
    return this.request(`/scheduler/tasks/${id}`, { method: 'DELETE' });
  }

  // Skills (additional)
  async updateSkill(id: string, data: any) {
    return this.request<any>(`/skills/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // MCP
  async listMCPServers() {
    return this.request<any[]>('/mcp/servers');
  }

  async listMCPCategories() {
    return this.request<any[]>('/mcp/categories');
  }

  async installMCPServer(id: string, config?: Record<string, any>) {
    return this.request<any>(`/mcp/servers/${id}/install`, {
      method: 'POST',
      body: JSON.stringify(config || {}),
    });
  }

  async deleteMCPServer(id: string) {
    return this.request(`/mcp/servers/${id}`, { method: 'DELETE' });
  }

  // Traces (additional)
  async getTrace(traceId: string) {
    return this.request<any>(`/traces/${traceId}`);
  }

  // Eval
  async listEvalDatasets() {
    return this.request<any[]>('/eval/datasets');
  }

  async seedBuiltinDatasets() {
    return this.request<any>('/eval/datasets/seed-builtin', { method: 'POST' });
  }

  async runEvalDataset(id: string) {
    return this.request<any>(`/eval/datasets/${id}/run`, { method: 'POST' });
  }

  // Search
  async search(query: string, limit = 20) {
    return this.request<any[]>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  // Permissions
  async resolvePermission(toolCallId: string, decision: 'allow' | 'allow_session' | 'allow_always' | 'deny') {
    return this.request<any>(`/permissions/resolve`, {
      method: 'POST',
      body: JSON.stringify({ tool_call_id: toolCallId, decision }),
    });
  }

  // Terminal sandbox
  async executeCommand(command: string, timeout?: number) {
    return this.request<any>('/terminal/execute', {
      method: 'POST',
      body: JSON.stringify({ command, timeout }),
    });
  }

  // Notifications
  async listNotifications(limit = 50) {
    return this.request<any>(`/notifications/history?limit=${limit}`);
  }

  async clearNotifications() {
    return this.request<any>('/notifications/history', { method: 'DELETE' });
  }

}

export const api = new ApiClient();
