// API client for backend communication

const BASE_URL = '/api/v1';

export interface ApiError {
  detail: string;
}

class ApiClient {
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
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
    return this.request<any[]>('/agents');
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
    return this.request<any[]>('/sessions');
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
  chatStream(sessionId: string, message: string, onEvent: (event: any) => void): () => void {
    const url = `${BASE_URL}/sessions/${sessionId}/chat`;

    const abortController = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
      let currentEvent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.slice(5).trim();
            try {
              const data = JSON.parse(dataStr);
              onEvent({ event: currentEvent || 'text', data });
            } catch {
              onEvent({ event: currentEvent || 'text', data: dataStr });
            }
            currentEvent = '';
          } else if (trimmed === '') {
            currentEvent = '';
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

  async listWorkflowTemplates() {
    return this.request<any[]>('/workflows/templates/');
  }

  async createFromTemplate(templateId: string, params: Record<string, any>) {
    return this.request<any>(`/workflows/templates/${templateId}`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Crews
  async listCrews() {
    return this.request<any[]>('/crews/');
  }

  async createCrew(data: any) {
    return this.request<any>('/crews/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async runCrew(id: string, inputs?: Record<string, string>) {
    return this.request<any>(`/crews/${id}/run`, {
      method: 'POST',
      body: JSON.stringify(inputs || {}),
    });
  }

  async updateCrew(id: string, data: any) {
    return this.request<any>(`/crews/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
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

  // User profile
  async getProfile() {
    return this.request<any>('/auth/me');
  }

  // Skills toggle
  async enableSkill(skillId: string) {
    return this.request<any>(`/skills/${skillId}/enable`, { method: 'POST' });
  }

  async disableSkill(skillId: string) {
    return this.request<any>(`/skills/${skillId}/disable`, { method: 'POST' });
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

  async deleteGroup(id: string) {
    return this.request<any>(`/groups/${id}`, { method: 'DELETE' });
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

  async updateGroupMember(groupId: string, memberId: string, data: Record<string, any>) {
    return this.request<any>(`/groups/${groupId}/members/${memberId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async listGroupMessages(groupId: string, limit = 50) {
    return this.request<any>(`/groups/${groupId}/messages?limit=${limit}`);
  }

  async sendGroupMessage(groupId: string, data: Record<string, any>) {
    return this.request<any>(`/groups/${groupId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
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

  async getPluginCategories() {
    return this.request<any[]>('/plugins/categories');
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

  async getPluginStatus(id: string) {
    return this.request<any>(`/plugins/${id}/status`);
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

  async installSkill(data: { name: string; description?: string; category?: string }) {
    return this.request<any>('/skills', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async toggleSkill(skillId: string, enabled: boolean) {
    const path = enabled ? `/skills/${skillId}/enable` : `/skills/${skillId}/disable`;
    return this.request<any>(path, { method: 'POST' });
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

    const response = await fetch(`${BASE_URL}/reason`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Reasoning failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async getReasoningTrace(traceId: string) {
    return this.request<any>(`/reason/${traceId}`);
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

  async getReasoningFeedback(traceId: string) {
    return this.request<any[]>(`/reason/${traceId}/feedback`);
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

  // Users
  async listUsers() {
    return this.request<any[]>('/users');
  }

  async switchUser(data: { user_id: string }) {
    return this.request<any>('/users/switch', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const api = new ApiClient();
