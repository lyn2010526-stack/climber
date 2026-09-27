import { API_BASE_URL as BASE_URL, getAuthHeaders } from './lib/api-client';
import { normalizeChatEvent, type ChatStreamEvent, type RawSSEEvent } from './types/chatEvents';

export interface ApiError {
  detail: string;
}

/**
 * A non-2xx answer. The status travels with the error so a caller can act on the
 * code — an approval the backend no longer holds answers 409, and only the code
 * says that — while the message stays the backend's `detail` for display.
 */
export class ApiRequestError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

/** SSE 空闲超时：连接静默多久后判定为挂起。长时生成每收到数据即重置。 */
const SSE_IDLE_TIMEOUT_MS = 120_000;

/** 连接静默超时。`idleTimeoutMs` 是空闲阈值，不是流的总时长。 */
export class SSEIdleTimeoutError extends Error {
  readonly idleTimeoutMs: number;

  constructor(idleTimeoutMs: number) {
    super(`SSE stream stayed idle for ${idleTimeoutMs}ms`);
    this.name = 'SSEIdleTimeoutError';
    this.idleTimeoutMs = idleTimeoutMs;
  }
}

export type { ChatStreamEvent, RawSSEEvent };

export interface TaskSummary {
  task_id: string;
  objective: string;
  status: string;
  progress: number;
  total_steps: number;
  created_at?: string | null;
}

export interface TaskDetail extends TaskSummary {
  result?: Record<string, unknown> | null;
  error?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface TaskSubmitRequest {
  task_type: 'agent_run' | 'data_processing' | 'workflow';
  payload: Record<string, unknown>;
}

export interface SessionMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string | null;
  tool_call_id: string | null;
  tool_calls: Array<{
    id: string;
    name?: string;
    arguments?: Record<string, unknown>;
    function?: { name?: string; arguments?: string | Record<string, unknown> };
  }>;
  tool_name: string | null;
  created_at: string;
}

export interface ArcBenchStatus {
  available: boolean;
  message: string;
  output_dir?: string | null;
  phase: string;
  phase_detail: string;
  trace_path?: string | null;
  trace_exists: boolean;
  acceptance?: {
    ran: boolean;
    passed: number;
    failed: number;
    unverified: number;
    note: string;
  } | null;
  last_events?: Array<{
    type: string;
    timestamp?: string | null;
    data: Record<string, unknown>;
  }>;
  pack_artifact?: string | null;
  pack_exists: boolean;
  updated_at?: string | null;
}

/** One rule as `GET /permissions/config` returns it. */
export interface PermissionRuleOut {
  decision: string;
  tool: string;
  pattern: string | null;
  description: string;
}

/** Payload of `GET /api/v1/permissions/config`. */
export interface PermissionConfigOut {
  mode: string;
  rules: PermissionRuleOut[];
  allowed_tools: string[];
  denied_tools: string[];
}

/** Body of `PUT /api/v1/permissions/config`; every field is optional server-side. */
export interface PermissionConfigUpdate {
  mode?: string;
  rules?: Array<{
    decision: string;
    tool: string;
    pattern?: string | null;
    description?: string;
  }>;
  allowed_tools?: string[];
  denied_tools?: string[];
}

interface SSEMessage {
  event: string;
  data: any;
}

/**
 * 读取 SSE 流。
 *
 * `idleTimeoutMs` 是**空闲**超时而非总时长：每收到一个数据块就重置计时器，
 * 因此长时生成不会误杀，只在连接静默后判定为挂起。超时抛出 `SSEIdleTimeoutError`，
 * 由调用方转成 `error` 事件收尾。
 */
async function readSSEStream(
  body: ReadableStream<Uint8Array>,
  onMessage: (message: SSEMessage) => void,
  idleTimeoutMs: number = SSE_IDLE_TIMEOUT_MS,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let idleTimer: ReturnType<typeof setTimeout> | undefined;
  let idleTimedOut = false;

  const clearIdleTimer = () => {
    if (idleTimer !== undefined) {
      clearTimeout(idleTimer);
      idleTimer = undefined;
    }
  };

  const armIdleTimer = () => {
    clearIdleTimer();
    idleTimer = setTimeout(() => {
      // 先记标记再取消 reader：取消只会让 read() 以 done 收尾，
      // 真正的失败信号由循环结束后的显式抛出给出。
      idleTimedOut = true;
      void reader.cancel().catch(() => undefined);
    }, idleTimeoutMs);
  };

  try {
    armIdleTimer();
    while (true) {
      let result: ReadableStreamReadResult<Uint8Array>;
      try {
        result = await reader.read();
      } catch (err) {
        if (idleTimedOut) throw new SSEIdleTimeoutError(idleTimeoutMs);
        throw err;
      }
      const { done, value } = result;
      if (done) break;
      armIdleTimer();

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        let eventName = '';
        let dataStr = '';

        for (const line of block.split('\n')) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            eventName = trimmed.slice(6).trim();
          } else if (trimmed.startsWith('data:')) {
            dataStr += trimmed.slice(5).trim();
          }
        }

        if (!dataStr || dataStr === '[DONE]') continue;

        try {
          onMessage({ event: eventName, data: JSON.parse(dataStr) });
        } catch {
          onMessage({ event: eventName, data: dataStr });
        }
      }
    }

    if (idleTimedOut) throw new SSEIdleTimeoutError(idleTimeoutMs);

    if (buffer.trim()) {
      // 服务端可能在最后一个块里省略结尾空行，补发一次尾帧。
      for (const line of buffer.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const dataStr = trimmed.slice(5).trim();
        if (!dataStr || dataStr === '[DONE]') continue;
        const eventName = buffer.split('\n').find(l => l.trim().startsWith('event:'))?.slice(6).trim() ?? '';
        try {
          onMessage({ event: eventName, data: JSON.parse(dataStr) });
        } catch {
          onMessage({ event: eventName, data: dataStr });
        }
      }
    }
  } finally {
    clearIdleTimer();
    reader.releaseLock();
  }
}

class ApiClient {
  private readStorage(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  private writeStorage(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      // Authentication can continue for the current request when storage is unavailable.
    }
  }

  private removeStorage(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore storage failures during cleanup.
    }
  }

  private getAuthHeaders(): Record<string, string> {
    return getAuthHeaders();
  }

  private async refreshToken(): Promise<string | null> {
    const refreshToken = this.readStorage('refresh_token');
    if (!refreshToken) return null;

    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) return null;

      const data = await response.json();
      if (!data.access_token) return null;
      this.writeStorage('auth_token', data.access_token);
      return data.access_token;
    } catch {
      return null;
    }
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...options.headers as Record<string, string>,
    };

    let response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      const newToken = await this.refreshToken();
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`;
        response = await fetch(`${BASE_URL}${path}`, {
          ...options,
          headers,
        });
      } else {
        this.removeStorage('auth_token');
        this.removeStorage('refresh_token');
        this.removeStorage('user_info');
        throw new Error('Authentication required');
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new ApiRequestError(response.status, error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Agents
  async listAgents() {
    const response = await this.request<any[] | { items: any[] }>('/agents');
    return Array.isArray(response) ? response : response.items ?? [];
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
    return Array.isArray(response) ? response : response.items ?? [];
  }

  async createSession(data: {
    title?: string;
    agent_id?: string;
    model_settings?: { provider?: string | null; model_id?: string; base_url?: string; credential_id?: string } | null;
  }) {
    return this.request<any>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteSession(id: string) {
    return this.request(`/sessions/${id}`, { method: 'DELETE' });
  }

  async getSessionMessages(sessionId: string): Promise<SessionMessage[]> {
    const response = await this.request<{ messages: SessionMessage[] }>(`/sessions/${sessionId}/messages`);
    return response.messages;
  }

  // Chat (SSE)
  chatStream(
    sessionId: string,
    message: string,
    onEvent: (event: ChatStreamEvent) => void,
    options: { idleTimeoutMs?: number } = {},
  ): () => void {
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

      if (!response.body) {
        onEvent({ type: 'error', message: 'The server returned an empty response body.' });
        return;
      }

      await readSSEStream(
        response.body,
        (frame) => onEvent(normalizeChatEvent(frame)),
        options.idleTimeoutMs,
      );
    }).catch((err) => {
      if (err.name === 'AbortError') return;
      onEvent({ type: 'error', message: err?.message || 'Request failed' });
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
      body: JSON.stringify({ inputs: inputs || {} }),
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
      body: JSON.stringify({ inputs: inputs || {} }),
    });
  }

  // API Keys (model-provider credentials for agent factory; reads the
  // api_keys table that _factory_agent_payload queries)
  async listApiKeys() {
    return this.request<any>('/api-keys');
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

  async createGroup(data: { name: string; description?: string; topic?: string; template?: 'default' }) {
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
    return this.request<any>('/doctor/');
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
  ): Promise<any> {
    const body = { task, mode, max_paths: maxPaths, max_refine_rounds: maxRefineRounds, coverage_enabled: coverageEnabled };

    return this.request<any>('/reason', {
      method: 'POST',
      body: JSON.stringify(body),
    });
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

  // Tasks
  async listTasks(params?: { status?: string; limit?: number }): Promise<TaskSummary[]> {
    const search = new URLSearchParams();
    if (params?.status) search.set('status', params.status);
    if (params?.limit) search.set('limit', String(params.limit));
    const qs = search.size ? `?${search.toString()}` : '';
    return this.request<TaskSummary[]>(`/tasks/${qs}`);
  }

  async getTask(taskId: string): Promise<TaskDetail> {
    return this.request<TaskDetail>(`/tasks/${taskId}`);
  }

  async createTask(data: TaskSubmitRequest): Promise<TaskDetail> {
    return this.request<TaskDetail>('/tasks/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async stopTask(id: string) {
    return this.request<{ task_id: string; cancelled: boolean }>(`/tasks/${id}/cancel`, { method: 'POST' });
  }

  // Terminal
  async executeSandboxCommand(command: string, timeout?: number): Promise<{ command: string; output: string; success: boolean }> {
    return this.request('/terminal/execute', {
      method: 'POST',
      body: JSON.stringify({ command, timeout }),
    });
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

  async runAutonomousSkill(data: any) {
    return this.request<any>('/skills/autonomous/run', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  runAutonomousSkillStream(
    data: { goal: string; skills: string[]; prompt_template: string },
    onEvent: (event: { type: string; data: unknown }) => void,
    onClose?: () => void,
  ): () => void {
    const url = `${BASE_URL}/skills/autonomous/run`;
    const abortController = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
      body: JSON.stringify(data),
      signal: abortController.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: response.statusText }));
          throw new Error(error.detail || `HTTP ${response.status}`);
        }

        if (!response.body) {
          onEvent({ type: 'error', data: { detail: 'The server returned an empty response body.' } });
          return;
        }

        await readSSEStream(response.body, (frame) => {
          // 该端点已按 AG-UI 风格把类型放进 `data.type`；缺失时回落到 `event:` 行。
          const payload =
            frame.data && typeof frame.data === 'object' ? (frame.data as Record<string, unknown>) : null;
          const nestedType = typeof payload?.type === 'string' ? payload.type : undefined;
          onEvent({
            type: nestedType || frame.event || 'message',
            data: nestedType ? payload?.data : frame.data,
          });
        });
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        onEvent({ type: 'error', data: { detail: err?.message || 'Request failed' } });
      })
      .finally(() => onClose?.());

    return () => abortController.abort();
  }

  async getArcbenchStatus(): Promise<ArcBenchStatus> {
    return this.request<ArcBenchStatus>('/arcbench/status');
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

  async runEvaluation(datasetId: string, agentId: string) {
    return this.request<any>('/eval/run', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, agent_id: agentId }),
    });
  }

  // Search
  async search(query: string, limit = 20) {
    return this.request<any[]>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  // Permissions
  async resolvePermission(toolCallId: string, decision: 'approve' | 'deny') {
    return this.request<any>(`/permissions/resolve`, {
      method: 'POST',
      body: JSON.stringify({ tool_call_id: toolCallId, decision }),
    });
  }

  /**
   * GET /api/v1/permissions/config. `mode` is a bare string because the server
   * serialises `PermissionMode` verbatim; callers narrow it with
   * `normalizePermissionMode` instead of casting.
   */
  async getPermissionConfig(): Promise<PermissionConfigOut> {
    return this.request<PermissionConfigOut>('/permissions/config');
  }

  /** PUT /api/v1/permissions/config. Requires an admin token. */
  async updatePermissionConfig(update: PermissionConfigUpdate): Promise<{ status: string; mode: string }> {
    return this.request<{ status: string; mode: string }>('/permissions/config', {
      method: 'PUT',
      body: JSON.stringify(update),
    });
  }

  // Auth
  async login(username: string, password: string) {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }
    return response.json();
  }

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
  }

  async getCurrentUser() {
    return this.request<any>('/auth/me');
  }

  async getAuthHealth() {
    const response = await fetch(`${BASE_URL}/auth/health`);
    if (response.ok) {
      return response.json();
    }
    return { authentication_enabled: false };
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${BASE_URL}/health`, { headers: { Accept: 'application/json' } });
      return response.ok;
    } catch {
      return false;
    }
  }

  async listAuthApiKeys() {
    return this.request<any>('/auth/keys');
  }

  async createAuthApiKey(data: { name: string; owner?: string; scopes: string[]; ttl_days: number | null }) {
    return this.request<any>('/auth/keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async revokeAuthApiKey(keyId: string) {
    return this.request<any>(`/auth/keys/${keyId}`, { method: 'DELETE' });
  }

  async changePassword(currentPassword: string, newPassword: string) {
    return this.request<any>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  }

}

export const api = new ApiClient();
