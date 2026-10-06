import { API_BASE_URL as BASE_URL, getAuthHeaders } from './lib/api-client';
import {
  normalizeChatEvent,
  parseRuntimeReport,
  parseSessionInput,
  type ChatStreamEvent,
  type RawSSEEvent,
  type RuntimeReport,
  type SessionInput,
  type SessionInputKind,
} from './types/chatEvents';
import type {
  ActionResponse,
  AgentMutationResponse,
  ApiKeyMutationResponse,
  AuthKeyMutationResponse,
  CrewMutationResponse,
  EvaluationAssessResponse,
  EvaluationRunResponse,
  GroupMutationResponse,
  InstructionUnderstandingResponse,
  PermissionResolutionResponse,
  PluginMutationResponse,
  ReasoningTraceResponse,
  SchedulerTaskResponse,
  SettingsResponse,
  StatsResponse,
  WorkflowMutationResponse,
} from './types/api';
import i18n from './i18n/config';

/**
 * Read a response body through a clone when the runtime exposes one.
 *
 * Cloning tees the body, so two readers that were handed the same `Response`
 * (two panels mounting against one fetch) both get their JSON instead of the
 * second one throwing "Body is unusable". Minimal test doubles expose only
 * `json()`, so those are read directly.
 */
function readBody(response: Response): Promise<unknown> {
  const readable = typeof (response as { clone?: unknown }).clone === 'function' ? response.clone() : response;
  return readable.json();
}

/**
 * Turn any error body into a display string.
 *
 * FastAPI returns `detail` as a string for handled errors but as an array of
 * `{ loc, msg, type }` objects for 422 validation failures. Coercing the array
 * directly produced "[object Object]"; flatten `msg` fields instead (R12-H62).
 */
function errorMessageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map(entry => (entry && typeof entry === 'object' && typeof (entry as { msg?: unknown }).msg === 'string'
          ? (entry as { msg: string }).msg
          : typeof entry === 'string' ? entry : ''))
        .filter(Boolean);
      if (parts.length) return parts.join('; ');
    }
    const message = (body as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) return message;
  }
  return fallback;
}

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
  /** Parsed error body, kept for callers that branch on server error codes. */
  readonly data?: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.data = data;
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

export interface SubtaskItem {
  id: string;
  description: string;
  status: string;
  dependencies: string[];
  result?: unknown;
  error?: string;
  claimed_by?: string;
  claimed_at?: string;
  completed_at?: string;
  lease_expires_at?: number;
}

export interface SubtaskListResponse {
  task_id: string;
  subtasks: SubtaskItem[];
}

export interface ClaimSubtasksResponse {
  task_id: string;
  subtasks: SubtaskItem[];
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
  metadata?: { images?: string[]; attachments?: Array<{ kind: 'image' | 'file'; name: string; mime_type: string; size: number }> };
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

export type PermissionTier = 'read_only' | 'partial_write' | 'full_write';

/** Payload of `GET /api/v1/permissions/config`. */
export interface PermissionConfigOut {
  mode: string;
  tier: PermissionTier;
  rules: PermissionRuleOut[];
  allowed_tools: string[];
  denied_tools: string[];
}

/** Body of `PUT /api/v1/permissions/config`; every field is optional server-side. */
export interface PermissionConfigUpdate {
  mode?: string;
  tier?: PermissionTier;
  rules?: Array<{
    decision: string;
    tool: string;
    pattern?: string | null;
    description?: string;
  }>;
  allowed_tools?: string[];
  denied_tools?: string[];
}

export interface ModelCatalogEntry {
  provider: string;
  model_id: string;
  label?: string | null;
}

/** One model as `GET /models/discover` returns it. */
export interface DiscoveredModel {
  provider: string;
  model_id: string;
  label: string;
}

/** Payload of `GET /api/v1/models/discover?credential_id=...`. */
export interface ModelDiscoveryResult {
  credential_id: string;
  provider: string;
  source: 'provider_api';
  status: 'ok' | 'empty';
  models: DiscoveredModel[];
}

export interface ModelApiKeyInput {
  provider: string;
  name: string;
  api_key: string;
  base_url?: string;
}

export interface AgentSummary {
  id: string;
  name: string;
  provider?: string | null;
  model_id?: string | null;
  description?: string | null;
  is_active?: boolean;
  created_at?: string | null;
}

export interface SessionListItem {
  id: string;
  title?: string | null;
  status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  provider?: string | null;
  model_id?: string | null;
  agent_id?: string | null;
}

export interface SessionCreateResult {
  id?: string;
  session_id?: string;
  title?: string | null;
  status?: string | null;
  provider?: string | null;
  model_id?: string | null;
}

/** POST /api/v1/tasks/{id}/{pause|resume|retry|rollback} response; the action key mirrors the verb. */
export interface TaskActionResult {
  task_id: string;
  pause?: boolean;
  resume?: boolean;
  retry?: boolean;
  rollback?: boolean;
}

/** One checkpoint as stored under a session by /sessions/{id}/checkpoint. */
export interface SessionCheckpoint {
  id: string;
  session_id: string;
  iteration: number;
  status: string;
  messages: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CheckpointSaveResult {
  status: string;
  session_id: string;
  checkpoint_id: string;
  total: number;
}

export interface CheckpointHistoryResult {
  session_id: string;
  checkpoints: SessionCheckpoint[];
}

export interface ForkSessionResult {
  session_id: string;
  status: string;
}

export interface ResumeSessionResult {
  session_id: string;
  status: string;
  checkpoint: SessionCheckpoint;
  messages: Array<Record<string, unknown>>;
  iteration_count: number;
  total_tokens: number;
}

export interface AuthHealthOut {
  authentication_enabled: boolean;
}

export interface CurrentUserOut {
  id?: string | number;
  username?: string;
  name?: string | null;
  email?: string | null;
  role?: string;
  scopes?: string[];
}

export interface GroupMemberOut {
  id: string;
  agent_id: string | null;
  role: string;
  status?: string;
}

export interface GroupOut {
  id: string;
  name: string;
  description?: string | null;
  topic?: string | null;
  member_count?: number;
  status?: string;
  members?: GroupMemberOut[];
  created_at?: string | null;
}

export interface GroupMessagesOut {
  messages: Array<{
    id: string;
    sender_name: string;
    content: string;
    created_at: string;
  }>;
}

/** One node of a group's task tree as `GET /groups/{id}/snapshot` returns it. */
export interface GroupTaskNode {
  node_id: string;
  parent_id: string | null;
  task_name: string;
  status: string;
  elapsed_ms: number;
}

/** Payload of `GET /api/v1/groups/{id}/snapshot`. */
export interface GroupSnapshot {
  group_id: string;
  task_tree: { task_id: string; nodes: GroupTaskNode[] } | null;
  history_scope: string;
}

export interface ClusterNodeOut {
  id: string;
  name?: string | null;
  status?: string;
  role?: string | null;
  endpoint?: string | null;
}

export interface ClusterStatusOut {
  status?: string;
  total_nodes?: number;
  online_nodes?: number;
  nodes?: ClusterNodeOut[];
  plan?: Array<{ id?: string | number; description?: string; task?: string; status?: string }>;
}

export interface CostUsageOut {
  total_cost?: number;
  total_tokens?: number;
  total_calls?: number;
  by_model?: Array<{ model: string; cost: number; tokens: number; calls: number }>;
  by_day?: Array<{ date: string; cost: number; tokens: number }>;
  cache_hit_rate?: number;
  [key: string]: unknown;
}

export interface CostBudgetOut {
  amount: number;
  period: string;
  is_active: boolean;
  current_spend: number;
  per_session_limit: number | null;
  per_request_limit: number | null;
}

export interface CostRecordOut {
  id: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  input_cost: number;
  output_cost: number;
  total_cost: number;
  created_at: string;
}

export interface ReasoningModeOut {
  id: string;
  name: string;
  description: string;
  available: boolean;
}

export interface ReasoningResultOut {
  answer: string;
  mode_used: string;
  candidates: Array<{
    id: string;
    strategy: string;
    path_type: string;
    content: string;
    confidence: number;
    metadata: Record<string, unknown>;
  }>;
  coverage: {
    score: number;
    edge_cases_count: number;
    risks_count: number;
    assumptions_count: number;
    blind_spots_count: number;
    high_risks: number;
    checklist: Record<string, boolean>;
  } | null;
  total_duration_ms: number;
  trace: {
    trace_id: string;
    path_traces: Array<{
      candidate_id: string;
      path_type: string;
      rounds: Array<{ round_num: number; action: string; output_summary: string }>;
      final_confidence: number;
    }>;
    coverage_checks: unknown[];
    final_selection_reason: string;
  } | null;
}

export interface AuthApiKeyItem {
  id: string;
  name: string;
  owner: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string | null;
}

export interface AuthApiKeyListOut {
  keys: AuthApiKeyItem[];
}

export interface AuthApiKeyCreatedOut {
  id: string;
  raw_key: string;
}

/** One account rule document as `GET /ui/rules` returns it. */
export interface UiRuleDocument {
  id: string;
  kind: 'soul' | 'memory' | 'project';
  title: string;
  content: string;
  revision: string | null;
  scope: 'user';
}

/** Payload of `GET /api/v1/profile/settings`. */
export interface ProfileSettings {
  enabled: boolean;
  show_raw_profile: boolean;
  consent_required: boolean;
  consent_version: string | null;
  consented_at: string | null;
  notice_version: string;
  notice: string;
}

/** Body of `PUT /api/v1/profile/settings`. */
export interface ProfileSettingsUpdate {
  enabled: boolean;
  consent_version?: string;
  show_raw_profile: boolean;
}

export interface ChatCommandsOut {
  commands: Array<{
    name: string;
    aliases: string[];
    summary: string;
    usage: string;
    streaming: boolean;
    allowed_while_streaming: boolean;
    args: Array<{ name: string; required: boolean; choices: string[] | null; description: string }>;
  }>;
}

export interface PromptTemplateOut {
  id: string;
  name: string;
  description: string;
  content: string;
  variables: Record<string, string>;
  tags: string[];
  model_id: string | null;
  created_at: string;
  updated_at: string;
  is_builtin: boolean;
}

export interface PromptTemplateInput {
  name: string;
  content: string;
  description?: string;
  variables?: Record<string, string>;
  tags?: string[];
  model_id?: string | null;
}

export interface AuditLogEntry {
  id: string;
  session_id: string | null;
  user_id: string | null;
  action: string;
  severity: string;
  details: Record<string, unknown>;
  result: string;
  created_at: string | null;
}

export interface AuditLogOut {
  entries: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Integrations (app/api/v1/routes/integrations.py) ───

export interface DomesticIntegrationStatusOut {
  status: string;
  provider: {
    provider: string;
    enabled: boolean;
    mode: string;
    reason: string | null;
  };
}

export interface QQBotQrOut {
  status: string;
  provider: string;
  token?: string;
  expires_at?: string;
  reason?: string;
}

export interface LangGraphGraphsOut {
  graphs: string[];
  status: string;
}

export interface LangGraphInvokeOut {
  result: unknown;
  status: string;
}

export interface Mem0StatusOut {
  available: boolean;
  status: string;
}

export interface Mem0SearchOut {
  results: unknown[];
  status: string;
}

export interface Mem0AddOut {
  memory_id: string;
  status: string;
}

export interface AgentRunOut {
  content: string;
  confidence: number | null;
  tool_calls: unknown[];
  metadata: Record<string, unknown>;
  status: string;
}

// ─── Security policy (app/core/security/api.py) ───

export interface SecurityQuota {
  cpu_cores: number;
  memory_mb: number;
  disk_mb: number;
  network_kbps: number;
}

export interface SecurityQuotaRequest extends SecurityQuota {
  agent_id: string;
}

export interface SecurityQuotasOut {
  quotas: Record<string, SecurityQuota>;
  usage: Record<string, unknown>;
}

export interface SecurityFsConfigOut {
  allowed_paths: string[];
  blocked_paths: string[];
  read_only_paths: string[];
  max_file_size_mb: number;
  allowed_extensions: string[];
}

export type SecurityFsConfigRequest = SecurityFsConfigOut;

export interface NetworkAllowlistOut {
  allowed_domains: string[];
  strict_domain_mode: boolean;
}

export type GroupWebSocketFrame =
  | { type: 'ack'; data: { ok: boolean; id?: string; error?: string } }
  | { type: 'message'; data: { id?: string } }
  | { type: 'member_update'; data?: { id?: string; member_id?: string; status?: string } }
  | { type: 'task_update'; data?: { id?: string; member_id?: string; task_id?: string } }
  | { type: 'error'; error?: string }
  | { type: 'pong' }
  | { type: string; data?: unknown };

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
  const dispatch = (block: string) => {
    let event = '';
    const data: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    }
    const text = data.join('\n');
    if (!text || text === '[DONE]') return;
    let payload: unknown;
    try { payload = JSON.parse(text); } catch { payload = text; }
    onMessage({ event, data: payload });
  };

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
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || '';

      for (const block of blocks) dispatch(block);
    }

    if (idleTimedOut) throw new SSEIdleTimeoutError(idleTimeoutMs);

    buffer += decoder.decode();
    if (buffer.trim()) dispatch(buffer);
  } finally {
    clearIdleTimer();
    reader.releaseLock();
  }
}

/** Minimal SSE reader for the slash endpoint (same frame format as chat). */
async function readSlashStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';
      for (const block of blocks) emitSlashFrame(block, onEvent);
    }
    if (buffer.trim()) emitSlashFrame(buffer, onEvent);
  } finally {
    reader.releaseLock();
  }
}

function emitSlashFrame(block: string, onEvent: (event: ChatStreamEvent) => void): void {
  let eventName = '';
  let dataStr = '';
  for (const line of block.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('event:')) eventName = trimmed.slice(6).trim();
    else if (trimmed.startsWith('data:')) dataStr += trimmed.slice(5).trim();
  }
  if (!dataStr || dataStr === '[DONE]') return;
  let data: unknown = dataStr;
  try {
    data = JSON.parse(dataStr);
  } catch {
    // keep raw string
  }
  onEvent(normalizeChatEvent({ event: eventName, data }));
}

// Documents
export interface DocumentSummary {
  id: string;
  name: string;
  status: string;
  chunks: number;
  size: number;
}

export interface DocumentMutationResult {
  id: string;
  name: string;
  status: string;
  chunks: number;
}

export interface DocumentSearchResult {
  id: string;
  text: string;
  metadata?: { filename?: string; doc_id?: string; chunk_index?: number };
  score?: number;
}

export interface DocumentSearchResponse {
  query: string;
  results: DocumentSearchResult[];
  n_results: number;
}

// Skill versions & test cases (backend: app/api/v1/routes/skills.py)
export interface SkillVersion {
  id: string;
  version: string;
  prompt: string;
  tools: string[];
  author: string;
  changelog: string;
  is_active: boolean;
  created_at: string | null;
}

export interface SkillVersionsResponse {
  skill_id: string;
  active_version_id: string | null;
  versions: SkillVersion[];
}

export interface SkillVersionCreateInput {
  prompt?: string;
  tools?: string[];
  version?: string;
  author?: string;
  changelog?: string;
}

export interface SkillVersionMutationResponse {
  ok: boolean;
  skill_id: string;
  version_id: string;
  version: string;
  active_version_id: string;
  deprecated_version_ids: string[];
}

export interface SkillVersionActivateResponse {
  ok: boolean;
  skill_id: string;
  active_version_id: string;
  version: string;
  deprecated_version_ids: string[];
}

export interface SkillTestCase {
  id: string;
  skill_id: string;
  name: string;
  input_params: Record<string, unknown>;
  expected_output_contains: string;
  expected_tools: string[];
  timeout_seconds: number;
  is_active: boolean;
  created_at: string | null;
}

export interface SkillTestCaseListResponse {
  skill_id: string;
  test_cases: SkillTestCase[];
}

export interface SkillTestCaseCreateInput {
  name: string;
  input_params?: Record<string, unknown>;
  expected_output_contains?: string;
  expected_tools?: string[];
  timeout_seconds?: number;
}

export interface SkillTestCaseMutationResponse {
  ok: boolean;
  skill_id: string;
  test_case_id: string;
}

export interface SkillTestRunResult {
  test_id: string;
  skill_id?: string;
  passed: boolean;
  output?: string;
  duration_ms?: number;
  error?: string;
  source?: string;
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
      const error = await readBody(response).catch(() => ({ detail: 'Request failed' }));
      throw new ApiRequestError(response.status, errorMessageFrom(error, `HTTP ${response.status}`), error);
    }

    return readBody(response) as Promise<T>;
  }

  // Agents
  async listAgents(): Promise<AgentSummary[]> {
    const response = await this.request<AgentSummary[] | { items: AgentSummary[] }>('/agents');
    return Array.isArray(response) ? response : response.items ?? [];
  }

  async createAgent(data: any): Promise<AgentMutationResponse> {
    return this.request<AgentMutationResponse>('/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteAgent(id: string) {
    return this.request(`/agents/${id}`, { method: 'DELETE' });
  }

  // Sessions
  async listSessions(): Promise<SessionListItem[]> {
    const response = await this.request<SessionListItem[] | { items: SessionListItem[] }>('/sessions');
    return Array.isArray(response) ? response : response.items ?? [];
  }

  async createSession(data: {
    title?: string;
    agent_id?: string;
    model_settings?: { provider?: string | null; model_id?: string; base_url?: string; credential_id?: string } | null;
  }): Promise<SessionCreateResult> {
    return this.request<SessionCreateResult>('/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteSession(id: string) {
    return this.request(`/sessions/${id}`, { method: 'DELETE' });
  }

  // Session checkpoints
  /** POST /api/v1/sessions/{sessionId}/checkpoint — append a checkpoint (server keeps the last 50). */
  async saveCheckpoint(sessionId: string, data: { messages: Array<Record<string, unknown>>; iteration: number; status?: string; metadata?: Record<string, unknown> }): Promise<CheckpointSaveResult> {
    return this.request<CheckpointSaveResult>(`/sessions/${encodeURIComponent(sessionId)}/checkpoint`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** GET /api/v1/sessions/{sessionId}/checkpoint — latest checkpoint only (404 when none). */
  async getLatestCheckpoint(sessionId: string): Promise<SessionCheckpoint> {
    return this.request<SessionCheckpoint>(`/sessions/${encodeURIComponent(sessionId)}/checkpoint`);
  }

  /** GET /api/v1/sessions/{sessionId}/history — full checkpoint history. */
  async getCheckpointHistory(sessionId: string): Promise<CheckpointHistoryResult> {
    return this.request<CheckpointHistoryResult>(`/sessions/${encodeURIComponent(sessionId)}/history`);
  }

  /** POST /api/v1/sessions/{sessionId}/fork — copy the session into a new id. */
  async forkSession(sessionId: string, newSessionId?: string): Promise<ForkSessionResult> {
    return this.request<ForkSessionResult>(`/sessions/${encodeURIComponent(sessionId)}/fork`, {
      method: 'POST',
      body: JSON.stringify(newSessionId ? { new_session_id: newSessionId } : {}),
    });
  }

  /** POST /api/v1/sessions/{sessionId}/resume — return messages plus the latest checkpoint (404 when none). */
  async resumeSession(sessionId: string): Promise<ResumeSessionResult> {
    return this.request<ResumeSessionResult>(`/sessions/${encodeURIComponent(sessionId)}/resume`, { method: 'POST' });
  }

  async getSessionMessages(sessionId: string): Promise<SessionMessage[]> {
    const response = await this.request<{ messages: SessionMessage[] }>(`/sessions/${sessionId}/messages`);
    return response.messages;
  }

  async submitSessionInput(sessionId: string, input: { client_request_id: string; kind: SessionInputKind; message: string }): Promise<SessionInput> {
    const response = await this.request<SessionInput>(`/sessions/${encodeURIComponent(sessionId)}/inputs`, {
      method: 'POST', body: JSON.stringify(input), signal: AbortSignal.timeout(15000),
    });
    const item = parseSessionInput(response);
    if (!item) throw new Error(i18n.t('api_errors.input_ack_invalid'));
    return item;
  }

  async getSessionInputs(sessionId: string): Promise<SessionInput[]> {
    const response = await this.request<{ items: SessionInput[] }>(`/sessions/${encodeURIComponent(sessionId)}/inputs`, { signal: AbortSignal.timeout(10000) });
    if (!Array.isArray(response.items)) throw new Error(i18n.t('api_errors.input_snapshot_invalid'));
    return response.items.map(item => {
      const parsed = parseSessionInput(item);
      if (!parsed) throw new Error(i18n.t('api_errors.input_snapshot_item_invalid'));
      return parsed;
    });
  }

  async getSessionInputReport(sessionId: string): Promise<RuntimeReport> {
    const response = await this.request<unknown>(`/sessions/${encodeURIComponent(sessionId)}/inputs/report`, { signal: AbortSignal.timeout(10000) });
    return parseRuntimeReport(response);
  }

  async resumeSessionInputs(sessionId: string, reviewConfirmed: boolean): Promise<SessionInput[]> {
    if (reviewConfirmed !== true) throw new Error(i18n.t('api_errors.review_confirmation_required'));
    const response = await this.request<{ items: unknown[] }>(`/sessions/${encodeURIComponent(sessionId)}/inputs/resume`, {
      method: 'POST', body: JSON.stringify({ review_confirmed: true }), signal: AbortSignal.timeout(15000),
    });
    if (!Array.isArray(response.items)) throw new Error(i18n.t('api_errors.resume_input_invalid'));
    return response.items.map(value => {
      const item = parseSessionInput(value);
      if (!item) throw new Error(i18n.t('api_errors.resume_input_item_invalid'));
      return item;
    });
  }

  /** GET /api/v1/sessions/{sessionId}; `provider`/`model_id` are the effective model binding. */
  async getSession(sessionId: string): Promise<{ id: string; provider?: string | null; model_id?: string | null }> {
    return this.request(`/sessions/${sessionId}`);
  }

  /**
   * POST /api/v1/sessions/{sessionId}/slash with `/model provider:model_id`.
   *
   * The slash command is the only server-side write path for a session's
   * model binding (it persists `model_settings` and rebinds a warm session).
   * Replies are always SSE: synthetic `text`/`done` frames on success, an
   * `error` frame (`data.error`) when the command failed.
   */
  async setSessionModel(sessionId: string, provider: string, modelId: string): Promise<{ provider: string; modelId: string }> {
    const response = await fetch(`${BASE_URL}/sessions/${sessionId}/slash`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
      body: JSON.stringify({ message: `/model ${provider}:${modelId}` }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiRequestError(response.status, errorMessageFrom(error, `HTTP ${response.status}`));
    }
    if (!response.body) {
      throw new Error('The server returned an empty response body.');
    }

    let errorMessage = '';
    let applied: { provider: string; modelId: string } | null = null;
    await readSSEStream(response.body, (frame) => {
      const payload = frame.data && typeof frame.data === 'object' ? (frame.data as Record<string, unknown>) : {};
      const name = (typeof payload.type === 'string' && payload.type) || frame.event;
      if (name === 'error') {
        for (const key of ['error', 'detail', 'message']) {
          const value = payload[key];
          if (typeof value === 'string' && value.length > 0) {
            errorMessage = value;
            break;
          }
        }
        return;
      }
      if (name === 'done') {
        const donePayload =
          payload.payload && typeof payload.payload === 'object' ? (payload.payload as Record<string, unknown>) : {};
        const doneProvider = typeof donePayload.provider === 'string' ? donePayload.provider : provider;
        const doneModelId = typeof donePayload.model_id === 'string' ? donePayload.model_id : modelId;
        applied = { provider: doneProvider, modelId: doneModelId };
      }
    });

    if (errorMessage) throw new Error(errorMessage);
    return applied ?? { provider, modelId };
  }

  // Chat (SSE)
  /**
   * POST /api/v1/sessions/{sessionId}/chat.
   *
   * `options.attachments` carries optional image references (base64 data URLs
   * or http(s) URLs) sent as the backend `images` field; omitted entirely when
   * empty so older payloads stay byte-identical.
   */
  chatStream(
    sessionId: string,
    message: string,
    onEvent: (event: ChatStreamEvent) => void,
    options: { idleTimeoutMs?: number; attachments?: string[]; files?: Array<{ kind: 'image' | 'file'; data: string; name: string; mime_type: string; size: number }> } = {},
  ): () => void {
    const payload: Record<string, unknown> = { message };
    if (options.attachments?.length && !options.files?.length) {
      payload.images = options.attachments;
    }
    if (options.files?.length) payload.attachments = options.files;
    return this.sessionStream(sessionId, 'chat', onEvent, payload, options.idleTimeoutMs);
  }

  startSessionInputs(sessionId: string, onEvent: (event: ChatStreamEvent) => void): () => void {
    return this.sessionStream(sessionId, 'inputs/start', onEvent);
  }

  private sessionStream(
    sessionId: string,
    path: 'chat' | 'inputs/start',
    onEvent: (event: ChatStreamEvent) => void,
    payload?: Record<string, unknown>,
    idleTimeoutMs?: number,
  ): () => void {
    const url = `${BASE_URL}/sessions/${encodeURIComponent(sessionId)}/${path}`;
    const abortController = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
      ...(payload ? { body: JSON.stringify(payload) } : {}),
      signal: abortController.signal,
    }).then(async (response) => {
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new ApiRequestError(response.status, errorMessageFrom(error, `HTTP ${response.status}`));
      }

      if (!response.body) {
        onEvent({ type: 'error', message: 'The server returned an empty response body.' });
        return;
      }

      let finished = false;
      let hasTurns = path === 'inputs/start';
      await readSSEStream(
        response.body,
        (frame) => {
          const event = normalizeChatEvent(frame);
          if (event.type === 'turn_started' || event.type === 'turn_done') hasTurns = true;
          if (event.type === 'done' || event.type === 'error') finished = true;
          onEvent(event);
        },
        idleTimeoutMs,
      );
      if (hasTurns && !finished && !abortController.signal.aborted) throw new Error(i18n.t('api_errors.chat_ended_early'));
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
  async listModels(): Promise<ModelCatalogEntry[]> {
    const response = await this.request<ModelCatalogEntry[] | { items: ModelCatalogEntry[] }>('/models');
    return Array.isArray(response) ? response : response.items ?? [];
  }

  /** GET /api/v1/models/discover?credential_id=... — live provider-side discovery. */
  async discoverModels(credentialId: string, signal?: AbortSignal): Promise<ModelDiscoveryResult> {
    return this.request<ModelDiscoveryResult>(`/models/discover?credential_id=${encodeURIComponent(credentialId)}`, { signal });
  }

  // Workflows
  async listWorkflows() {
    return this.request<any[]>('/workflows/');
  }

  async createWorkflow(data: any): Promise<WorkflowMutationResponse> {
    return this.request<WorkflowMutationResponse>('/workflows/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateWorkflow(id: string, data: any): Promise<WorkflowMutationResponse> {
    return this.request<WorkflowMutationResponse>(`/workflows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async runWorkflow(id: string, inputs?: Record<string, string>): Promise<WorkflowMutationResponse> {
    return this.request<WorkflowMutationResponse>(`/workflows/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ inputs: inputs || {} }),
    });
  }

  async deleteWorkflow(id: string) {
    return this.request<any>(`/workflows/${id}`, { method: 'DELETE' });
  }

  async listWorkflowTemplates(): Promise<any[]> {
    return this.request<any[]>('/workflows/templates');
  }

  async createWorkflowFromTemplate(templateId: string, name?: string): Promise<WorkflowMutationResponse> {
    return this.request<WorkflowMutationResponse>(`/workflows/templates/${encodeURIComponent(templateId)}`, {
      method: 'POST',
      body: JSON.stringify(name ? { name } : {}),
    });
  }

  async importWorkflow(data: unknown): Promise<WorkflowMutationResponse> {
    return this.request<WorkflowMutationResponse>('/workflows/import', {
      method: 'POST',
      body: JSON.stringify({ data }),
    });
  }

  /**
   * Download a workflow export through the API client so auth headers apply.
   * The backend returns the file body with a Content-Disposition filename.
   */
  async exportWorkflow(id: string, format: 'json' | 'yaml' = 'json'): Promise<void> {
    const response = await fetch(`${BASE_URL}/workflows/${encodeURIComponent(id)}/export?format=${format}`, {
      headers: { Accept: format === 'yaml' ? 'application/x-yaml' : 'application/json', ...this.getAuthHeaders() },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      const detail = typeof error?.detail === 'string' ? error.detail : `HTTP ${response.status}`;
      throw new Error(detail);
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const filename = /filename=([^;]+)/.exec(disposition)?.[1]?.trim() || `workflow-${id}.${format}`;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  // Crews
  async listCrews() {
    return this.request<any[]>('/crews/');
  }

  async createCrew(data: any): Promise<CrewMutationResponse> {
    return this.request<CrewMutationResponse>('/crews/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async runCrew(id: string, inputs?: Record<string, string>): Promise<CrewMutationResponse> {
    return this.request<CrewMutationResponse>(`/crews/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ inputs: inputs || {} }),
    });
  }

  async deleteCrew(id: string) {
    return this.request(`/crews/${id}`, { method: 'DELETE' });
  }

  // API Keys (model-provider credentials for agent factory; reads the
  // api_keys table that _factory_agent_payload queries)
  async listApiKeys(signal?: AbortSignal): Promise<Array<{ id: string; name: string; provider: string; base_url?: string | null; is_active: boolean }>> {
    type StoredKey = { id: string; name: string; provider: string; base_url?: string | null; is_active: boolean };
    const response = await this.request<StoredKey[] | { items: StoredKey[] }>('/api-keys', { signal });
    return Array.isArray(response) ? response : response.items ?? [];
  }

  async addApiKey(data: ModelApiKeyInput): Promise<ApiKeyMutationResponse> {
    return this.request<ApiKeyMutationResponse>('/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteApiKey(id: string) {
    return this.request(`/api-keys/${id}`, { method: 'DELETE' });
  }

  // Stats
  async getStats(): Promise<StatsResponse> {
    return this.request<StatsResponse>('/stats');
  }

  // Skills toggle: `toggleSkill` (below) is the single entry point for
  // enabling/disabling a skill; it maps onto POST /skills/{id}/enable|disable.
  // The former standalone `enableSkill`/`disableSkill` wrappers were removed
  // because they duplicated `toggleSkill` and had no callers.

  // Cluster / Groups
  // The backend create endpoint requires `name`; endpoint/role/status/capabilities
  // are optional. Sending `requirements` was rejected as a missing name (R12-H61).
  async createCluster(data: { name: string; endpoint?: string; role?: string; status?: string; capabilities?: string[] }) {
    return this.request<any>('/cluster/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  getClusterStatus(): Promise<ClusterStatusOut> {
    return this.request<ClusterStatusOut>('/cluster/status');
  }

  /** GET /cluster — full node list; each entry matches ClusterNodeOut. */
  async listClusterNodes(): Promise<ClusterNodeOut[]> {
    return this.request<ClusterNodeOut[]>('/cluster');
  }

  /** DELETE /cluster/{nodeId} — admin-gated node removal (backend misc.py). */
  async deleteClusterNode(nodeId: string) {
    return this.request<any>(`/cluster/${encodeURIComponent(nodeId)}`, { method: 'DELETE' });
  }

  async listGroups() {
    return this.request<any[]>('/groups/');
  }

  async createGroup(data: { name: string; description?: string; topic?: string; template?: 'default' }): Promise<GroupMutationResponse> {
    return this.request<GroupMutationResponse>('/groups/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  getGroup(id: string): Promise<GroupOut> {
    return this.request<GroupOut>(`/groups/${id}`);
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

  listGroupMessages(groupId: string, limit = 50): Promise<GroupMessagesOut> {
    return this.request<GroupMessagesOut>(`/groups/${groupId}/messages?limit=${limit}`);
  }

  /** GET /api/v1/groups/ — id/name pairs for the anchored task-trace picker. */
  async listGroupsSimple(signal?: AbortSignal): Promise<Array<{ id: string; name: string }>> {
    return this.request('/groups/', { signal });
  }

  /** GET /api/v1/groups/{groupId}/snapshot — task tree for one group. */
  async getGroupSnapshot(groupId: string, signal?: AbortSignal): Promise<GroupSnapshot> {
    return this.request<GroupSnapshot>(`/groups/${encodeURIComponent(groupId)}/snapshot`, { signal });
  }

  // Documents
  async listDocuments(): Promise<DocumentSummary[]> {
    return this.request<DocumentSummary[]>('/documents/');
  }

  /**
   * POST /documents/ — JSON create. Uploads are read client-side via
   * `File.text()` and sent as `{ filename, content }`; the backend runs the
   * same chunk + vector-index pipeline as /documents/index-text.
   */
  async createDocument(data: { filename: string; content: string; content_type?: string; collection?: string }): Promise<DocumentMutationResult> {
    return this.request<DocumentMutationResult>('/documents/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteDocument(id: string): Promise<{ id: string; deleted: boolean }> {
    return this.request<{ id: string; deleted: boolean }>(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });
  }

  /**
   * POST /documents/search — `query`/`n_results` are query params in the
   * backend signature (no body model is declared).
   */
  async searchDocuments(query: string, nResults = 5): Promise<DocumentSearchResponse> {
    const params = new URLSearchParams({ query, n_results: String(nResults) });
    return this.request<DocumentSearchResponse>(`/documents/search?${params.toString()}`, { method: 'POST' });
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

  async installPlugin(id: string, config?: Record<string, any>): Promise<PluginMutationResponse> {
    return this.request<PluginMutationResponse>(`/plugins/${id}/install`, {
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

  async getPluginStatus(id: string): Promise<PluginMutationResponse> {
    return this.request<PluginMutationResponse>(`/plugins/${id}/status`);
  }

  async importPlugin(sourceUrl: string, name?: string, type?: string): Promise<PluginMutationResponse> {
    return this.request<PluginMutationResponse>('/plugins/import', {
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
  async listReasoningModes(): Promise<ReasoningModeOut[]> {
    const response = await this.request<ReasoningModeOut[] | { modes: ReasoningModeOut[] }>('/reason/modes');
    return Array.isArray(response) ? response : response.modes ?? [];
  }

  async reasonStream(
    task: string,
    mode: string,
    maxPaths: number,
    maxRefineRounds: number,
    coverageEnabled: boolean,
  ): Promise<ReasoningResultOut> {
    const body = { task, mode, max_paths: maxPaths, max_refine_rounds: maxRefineRounds, coverage_enabled: coverageEnabled };

    return this.request<ReasoningResultOut>('/reason', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async getReasoningTrace(traceId: string): Promise<ReasoningTraceResponse> {
    return this.request<ReasoningTraceResponse>(`/reason/${traceId}`);
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

  async listReasoningHistory(limit = 50, offset = 0) {
    return this.request<any[]>(`/reason/history?limit=${limit}&offset=${offset}`);
  }

  // Settings
  async getSettings(): Promise<SettingsResponse> {
    return this.request<SettingsResponse>('/settings/');
  }

  async updateSettings(data: Record<string, any>): Promise<SettingsResponse> {
    return this.request<SettingsResponse>('/settings/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // UI rules (account-level rule documents)
  /** GET /api/v1/ui/rules. */
  async getUiRules(): Promise<UiRuleDocument[]> {
    return this.request<UiRuleDocument[]>('/ui/rules', { method: 'GET' });
  }

  /** PUT /api/v1/ui/rules/{kind} — revision-guarded save; 409 signals a conflict. */
  async putUiRules(kind: string, body: { content: string; revision: string | null }): Promise<UiRuleDocument> {
    return this.request<UiRuleDocument>(`/ui/rules/${kind}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  // Profile (habit-learning settings)
  /** GET /api/v1/profile/settings. */
  async getProfileSettings(signal?: AbortSignal): Promise<ProfileSettings> {
    return this.request<ProfileSettings>('/profile/settings', { signal });
  }

  /** PUT /api/v1/profile/settings. */
  async putProfileSettings(settings: ProfileSettingsUpdate): Promise<ProfileSettings> {
    return this.request<ProfileSettings>('/profile/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
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

  /** POST /api/v1/tasks/{id}/pause — 409 when the task cannot be paused. */
  async pauseTask(id: string): Promise<TaskActionResult> {
    return this.request<TaskActionResult>(`/tasks/${id}/pause`, { method: 'POST' });
  }

  /** POST /api/v1/tasks/{id}/resume — 409 when the task is not paused. */
  async resumeTask(id: string): Promise<TaskActionResult> {
    return this.request<TaskActionResult>(`/tasks/${id}/resume`, { method: 'POST' });
  }

  /** POST /api/v1/tasks/{id}/retry — 409 when the task is not in a retryable state. */
  async retryTask(id: string): Promise<TaskActionResult> {
    return this.request<TaskActionResult>(`/tasks/${id}/retry`, { method: 'POST' });
  }

  /** POST /api/v1/tasks/{id}/rollback — 409 when the task has nothing to roll back. */
  async rollbackTask(id: string): Promise<TaskActionResult> {
    return this.request<TaskActionResult>(`/tasks/${id}/rollback`, { method: 'POST' });
  }

  async listSubtasks(taskId: string, status?: string): Promise<SubtaskListResponse> {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return this.request<SubtaskListResponse>(`/tasks/${taskId}/subtasks${qs}`);
  }

  async claimSubtasks(taskId: string, agentId: string, limit = 1, leaseSeconds = 900): Promise<ClaimSubtasksResponse> {
    return this.request<ClaimSubtasksResponse>(`/tasks/${taskId}/subtasks/claim`, {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId, limit, lease_seconds: leaseSeconds }),
    });
  }

  async completeSubtask(taskId: string, subtaskId: string, agentId: string, result?: unknown, error?: string): Promise<SubtaskItem> {
    return this.request<SubtaskItem>(`/tasks/${taskId}/subtasks/${subtaskId}/complete`, {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId, result, error: error ?? null }),
    });
  }

  // Terminal
  async executeSandboxCommand(command: string, timeout?: number): Promise<{ command: string; output: string; success: boolean }> {
    return this.request('/terminal/execute', {
      method: 'POST',
      body: JSON.stringify({ command, timeout }),
    });
  }

  // Cost
  getCostUsage(): Promise<CostUsageOut> {
    return this.request<CostUsageOut>('/cost/usage');
  }

  getCostBudget(): Promise<CostBudgetOut> {
    return this.request<CostBudgetOut>('/cost/budget');
  }

  // Cost records: one row per billed call, newest first. The anchored token
  // meter's per-turn trend reads the most recent 10 rows.
  async listCostRecords(sessionId = ''): Promise<CostRecordOut[]> {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
    return this.request<CostRecordOut[]>(`/cost/records${query}`);
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

  // Skill versioning (backend: app/api/v1/routes/skills.py)
  /** GET /skills/{skillId}/versions — list versions, marks the active one. */
  async listSkillVersions(skillId: string): Promise<SkillVersionsResponse> {
    return this.request<SkillVersionsResponse>(`/skills/${encodeURIComponent(skillId)}/versions`);
  }

  /** POST /skills/{skillId}/versions — snapshot current content as a new active version. */
  async createSkillVersion(skillId: string, data: SkillVersionCreateInput = {}): Promise<SkillVersionMutationResponse> {
    return this.request<SkillVersionMutationResponse>(`/skills/${encodeURIComponent(skillId)}/versions`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** POST /skills/{skillId}/versions/{versionId}/activate — roll back to a stored version. */
  async activateSkillVersion(skillId: string, versionId: string): Promise<SkillVersionActivateResponse> {
    return this.request<SkillVersionActivateResponse>(
      `/skills/${encodeURIComponent(skillId)}/versions/${encodeURIComponent(versionId)}/activate`,
      { method: 'POST' },
    );
  }

  // Skill test cases (backend: app/api/v1/routes/skills.py)
  /** GET /skills/{skillId}/test-cases — list test cases, newest first. */
  async listSkillTestCases(skillId: string): Promise<SkillTestCaseListResponse> {
    return this.request<SkillTestCaseListResponse>(`/skills/${encodeURIComponent(skillId)}/test-cases`);
  }

  /** POST /skills/{skillId}/test-cases — add a test case. */
  async createSkillTestCase(skillId: string, data: SkillTestCaseCreateInput): Promise<SkillTestCaseMutationResponse> {
    return this.request<SkillTestCaseMutationResponse>(`/skills/${encodeURIComponent(skillId)}/test-cases`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** POST /skills/{skillId}/test-cases/{caseId}/run — static-mode run, no LLM involved. */
  async runSkillTestCase(skillId: string, caseId: string): Promise<SkillTestRunResult> {
    return this.request<SkillTestRunResult>(
      `/skills/${encodeURIComponent(skillId)}/test-cases/${encodeURIComponent(caseId)}/run`,
      { method: 'POST' },
    );
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
          throw new Error(errorMessageFrom(error, `HTTP ${response.status}`));
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

  /** POST /eval/datasets — `data_json` may be a JSON-array string or an array. */
  async createEvalDataset(data: { name: string; description?: string; data_json: string | unknown[] }) {
    return this.request<any>('/eval/datasets', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async runEvaluation(datasetId: string, agentId: string): Promise<EvaluationRunResponse> {
    return this.request<EvaluationRunResponse>('/eval/run', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, agent_id: agentId }),
    });
  }

  /** POST /eval/assess — offline rubric scoring of arbitrary output. */
  async evaluateOutput(payload: {
    output: string;
    rubric: Array<{
      item_id: string;
      description?: string;
      contains_any?: string[];
      not_contains_any?: string[];
      weight?: number;
      essential?: boolean;
      veto?: boolean;
    }>;
    scenario_id?: string;
    expected_points?: string[];
  }): Promise<EvaluationAssessResponse> {
    return this.request<EvaluationAssessResponse>('/eval/assess', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /** GET /eval/reports — in-memory evaluation reports, most recent first. */
  async listEvalReports() {
    return this.request<any[]>('/eval/reports');
  }

  /** POST /instruction-traces/understand — read-only structured understanding. */
  async understandInstruction(rawText: string, context?: string): Promise<InstructionUnderstandingResponse> {
    return this.request<InstructionUnderstandingResponse>('/instruction-traces/understand', {
      method: 'POST',
      body: JSON.stringify({ raw_text: rawText, context: context ?? null }),
    });
  }

  // Search
  async search(query: string, limit = 20) {
    return this.request<any[]>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  }

  // Permissions
  // Decision values are the backend's: allow | allow_session | allow_always | deny.
  async resolvePermission(toolCallId: string, decision: 'allow' | 'deny'): Promise<PermissionResolutionResponse> {
    return this.request<PermissionResolutionResponse>(`/permissions/resolve`, {
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
  async updatePermissionConfig(update: PermissionConfigUpdate): Promise<{ status: string; mode: string; tier: PermissionTier }> {
    return this.request<{ status: string; mode: string; tier: PermissionTier }>('/permissions/config', {
      method: 'PUT',
      body: JSON.stringify(update),
    });
  }

  /** GET /api/v1/reasoning/permission-tiers. Admin-gated three-tier view. */
  async getPermissionTiers(): Promise<{
    tiers: Array<{ id: PermissionTier; mode: string }>;
    current: { mode: string | null; tier: PermissionTier | null };
    tool_states: Array<{ tool: string; decision: string }>;
  }> {
    return this.request('/reasoning/permission-tiers');
  }

  /** GET /api/v1/reasoning/levels — catalog of the three session thinking levels. */
  async getThinkingLevels(): Promise<{
    levels: Array<{ id: string; max_tokens?: number | null; temperature?: number | null; reasoning_effort?: string | null }>;
    default: string;
  }> {
    return this.request('/reasoning/levels');
  }

  /** GET /api/v1/reasoning/sessions/{sessionId}/reasoning-level. */
  async getSessionThinkingLevel(sessionId: string): Promise<{ session_id: string; level: string }> {
    return this.request(`/reasoning/sessions/${sessionId}/reasoning-level`);
  }

  /**
   * PUT /api/v1/reasoning/sessions/{sessionId}/reasoning-level.
   * `level` is one of `low|medium|high`; the server persists it on the
   * session's `context_data.reasoning_level`.
   */
  async updateSessionThinkingLevel(sessionId: string, level: string): Promise<{ session_id: string; level: string; updated?: boolean }> {
    return this.request(`/reasoning/sessions/${sessionId}/reasoning-level`, {
      method: 'PUT',
      body: JSON.stringify({ level }),
    });
  }

  /** GET /api/v1/chat-commands — authoritative slash command catalog. */
  async listChatCommands(): Promise<ChatCommandsOut['commands']> {
    const response = await fetch(`${BASE_URL}/chat-commands`, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new ApiRequestError(response.status, errorMessageFrom(null, `HTTP ${response.status}`));
    const data = await response.json() as ChatCommandsOut;
    return data?.commands ?? [];
  }

  /**
   * Open the group WebSocket: /api/v1/ws/groups/{groupId}.
   *
   * The URL is derived from the page origin because the browser WebSocket
   * handshake cannot ride the fetch proxy; auth stays at the transport layer
   * the backend expects (cookie/origin), matching the previous inline wiring.
   */
  openGroupWebSocket(groupId: string): WebSocket {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return new WebSocket(`${protocol}//${window.location.host}${BASE_URL}/ws/groups/${encodeURIComponent(groupId)}`);
  }

  /** POST /api/v1/sessions/{id}/slash — SSE reply, surfaced through chat events. */
  runSlashCommand(
    sessionId: string,
    message: string,
    onEvent: (event: ChatStreamEvent) => void,
    options: { signal?: AbortSignal } = {},
  ): () => void {
    const abortController = new AbortController();
    let terminal = false;
    const emit = (event: ChatStreamEvent) => {
      if (abortController.signal.aborted || terminal) return;
      if (event.type === 'done' || event.type === 'error') terminal = true;
      onEvent(event);
    };
    if (options.signal) {
      if (options.signal.aborted) abortController.abort();
      else options.signal.addEventListener('abort', () => abortController.abort(), { once: true });
    }

    fetch(`${BASE_URL}/sessions/${encodeURIComponent(sessionId)}/slash`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
      body: JSON.stringify({ message }),
      signal: abortController.signal,
    })
      .then(async response => {
        if (!response.ok) {
          const error = await response.json().catch(() => ({ detail: response.statusText }));
          throw new Error(error.detail || `HTTP ${response.status}`);
        }
        if (!response.body) {
          emit({ type: 'error', message: 'The server returned an empty response body.' });
          return;
        }
        await readSlashStream(response.body, emit);
        if (!terminal) emit({ type: 'error', message: 'The command response ended without a completion event.' });
      })
      .catch(err => {
        if (err.name === 'AbortError') return;
        emit({ type: 'error', message: err?.message || 'Request failed' });
      });

    return () => abortController.abort();
  }

  /** POST /api/v1/sessions/{id}/cancel — fire-and-forget server-side interrupt. */
  cancelSessionTurn(sessionId: string): void {
    fetch(`${BASE_URL}/sessions/${encodeURIComponent(sessionId)}/cancel`, {
      method: 'POST',
      headers: { ...this.getAuthHeaders() },
    }).catch(() => undefined);
  }

  /**
   * GET /api/v1/tasks/{taskId}/events — authenticated SSE subscription.
   *
   * Returns the raw `Response` so the caller owns stream consumption
   * (idle timeouts, Retry-After backoff, frame validation); headers and
   * the base URL stay centralised here.
   */
  async streamTaskEvents(taskId: string, signal: AbortSignal): Promise<Response> {
    return fetch(`${BASE_URL}/tasks/${encodeURIComponent(taskId)}/events`, {
      headers: { ...this.getAuthHeaders(), Accept: 'text/event-stream' },
      signal,
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
      throw new ApiRequestError(response.status, errorMessageFrom(error, 'Login failed'));
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

  getCurrentUser(): Promise<CurrentUserOut> {
    return this.request<CurrentUserOut>('/auth/me');
  }

  async getAuthHealth(): Promise<AuthHealthOut> {
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

  listAuthApiKeys(): Promise<AuthApiKeyListOut> {
    return this.request<AuthApiKeyListOut>('/auth/keys');
  }

  async createAuthApiKey(data: { name: string; owner?: string; scopes: string[]; ttl_days: number | null }): Promise<AuthApiKeyCreatedOut> {
    return this.request<AuthApiKeyCreatedOut>('/auth/keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async revokeAuthApiKey(keyId: string): Promise<AuthKeyMutationResponse> {
    return this.request<AuthKeyMutationResponse>(`/auth/keys/${keyId}`, { method: 'DELETE' });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<AuthKeyMutationResponse> {
    return this.request<AuthKeyMutationResponse>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  }

  /** GET /api/v1/cost/quota — per-day request/token and monthly cost ceilings. */
  async getCostQuota() {
    return this.request<{
      max_requests_per_day?: number;
      max_tokens_per_day?: number;
      max_cost_per_month?: number;
      requests_today?: number;
      tokens_today?: number;
      cost_this_month?: number;
    }>('/cost/quota');
  }

  /** GET /api/v1/memory/sidecars/{scope} — read-only L0/L1 sidecar records. */
  async listMemorySidecars(scope: string, level?: 0 | 1 | 2) {
    const query = level === undefined ? '' : `?level=${level}`;
    return this.request<{
      scope: string;
      records: Array<{
        id: string;
        level: number;
        scope: string;
        body: string;
        generated_by: string;
        updated_at: string | null;
      }>;
    }>(`/memory/sidecars/${scope.split('/').map(encodeURIComponent).join('/')}${query}`);
  }

  /** GET /api/v1/memory/archives — newest-first archives for one session. */
  async listMemoryArchives(sessionId: string, limit = 20) {
    return this.request<{
      total: number;
      archives: Array<{
        id: string;
        session_id: string;
        title: string | null;
        one_line_summary: string;
        message_count: number;
        archive_status: string;
        created_at: string | null;
      }>;
    }>(`/memory/archives?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`);
  }

  /** GET /api/v1/memory/archives/{archiveId} — one structured session archive. */
  async getMemoryArchive(archiveId: string) {
    return this.request<{
      id: string;
      session_id: string;
      title: string | null;
      one_line_summary: string;
      message_count: number;
      messages: Array<{ role: string; content: string }>;
      memory_diff: Record<string, unknown> | null;
      archive_status: string;
      created_at: string | null;
    }>(`/memory/archives/${encodeURIComponent(archiveId)}`);
  }

  /** GET /api/v1/memory/context-bundle — token-cheap L0 summary bundle. */
  async getMemoryContextBundle(options?: { query?: string; sessionId?: string; includeL1?: boolean }) {
    const params = new URLSearchParams();
    if (options?.query) params.set('query', options.query);
    if (options?.sessionId) params.set('session_id', options.sessionId);
    if (options?.includeL1) params.set('include_l1', 'true');
    const query = params.size > 0 ? `?${params.toString()}` : '';
    return this.request<{
      content: string;
      injected_summaries: number;
      memory_hits: number;
      scopes: Array<{ scope: string; abstract: string; overview: string }>;
      hits: Array<{ memory_type: string; content: string }>;
      session_id?: string;
    }>(`/memory/context-bundle${query}`);
  }

  /** GET /api/v1/observability/audit-log — paginated durable audit events. */
  async listAuditLog(options?: {
    limit?: number;
    offset?: number;
    action?: string;
    severity?: string;
    sessionId?: string;
    userId?: string;
  }) {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) params.set('limit', String(options.limit));
    if (options?.offset !== undefined) params.set('offset', String(options.offset));
    if (options?.action) params.set('action', options.action);
    if (options?.severity) params.set('severity', options.severity);
    if (options?.sessionId) params.set('session_id', options.sessionId);
    if (options?.userId) params.set('user_id', options.userId);
    const query = params.size > 0 ? `?${params.toString()}` : '';
    return this.request<AuditLogOut>(`/observability/audit-log${query}`);
  }

  // Integrations (app/api/v1/routes/integrations.py)

  /** GET /api/v1/integrations/domestic/status — QQBot provider status. */
  async getDomesticIntegrationStatus(): Promise<DomesticIntegrationStatusOut> {
    return this.request<DomesticIntegrationStatusOut>('/integrations/domestic/status');
  }

  /** POST /api/v1/integrations/domestic/qqbot/qr — issue a binding QR token. */
  async createQQBotQr(): Promise<QQBotQrOut> {
    return this.request<QQBotQrOut>('/integrations/domestic/qqbot/qr', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  /** GET /api/v1/integrations/langgraph/graphs — registered graph names. */
  async listLangGraphGraphs(): Promise<LangGraphGraphsOut> {
    return this.request<LangGraphGraphsOut>('/integrations/langgraph/graphs');
  }

  /** POST /api/v1/integrations/langgraph/{graphName}/invoke. Requires admin. */
  async invokeLangGraph(graphName: string, payload: { inputs?: Record<string, unknown>; config?: Record<string, unknown> }): Promise<LangGraphInvokeOut> {
    return this.request<LangGraphInvokeOut>(`/integrations/langgraph/${encodeURIComponent(graphName)}/invoke`, {
      method: 'POST',
      body: JSON.stringify({ inputs: payload.inputs ?? {}, config: payload.config ?? {} }),
    });
  }

  /** GET /api/v1/integrations/mem0/status — service availability. */
  async getMem0Status(): Promise<Mem0StatusOut> {
    return this.request<Mem0StatusOut>('/integrations/mem0/status');
  }

  /** POST /api/v1/integrations/mem0/search — caller-scoped memory search. */
  async mem0Search(payload: { query: string; limit?: number; user_id?: string }): Promise<Mem0SearchOut> {
    return this.request<Mem0SearchOut>('/integrations/mem0/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /** POST /api/v1/integrations/mem0/add — add a memory under the caller's namespace. */
  async mem0Add(payload: { content: string; metadata?: Record<string, unknown>; user_id?: string }): Promise<Mem0AddOut> {
    return this.request<Mem0AddOut>('/integrations/mem0/add', {
      method: 'POST',
      body: JSON.stringify({ content: payload.content, metadata: payload.metadata ?? {}, ...(payload.user_id ? { user_id: payload.user_id } : {}) }),
    });
  }

  /** POST /api/v1/integrations/agent/run — run a Pydantic-AI agent. Requires admin. */
  async runIntegrationAgent(payload: { prompt: string; system_prompt?: string; model?: string }): Promise<AgentRunOut> {
    return this.request<AgentRunOut>('/integrations/agent/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Security policy (app/core/security/api.py, mounted at /api/v1/security; all admin-gated)

  /** GET /api/v1/security/quotas — per-agent quotas and current usage. */
  async getSecurityQuotas(): Promise<SecurityQuotasOut> {
    return this.request<SecurityQuotasOut>('/security/quotas');
  }

  /** PUT /api/v1/security/quotas — set the quota for one agent. */
  async updateSecurityQuota(payload: SecurityQuotaRequest): Promise<{ status: string; agent_id: string; quota: SecurityQuota }> {
    return this.request('/security/quotas', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  /** GET /api/v1/security/fs-config — file-system isolation config. */
  async getSecurityFsConfig(): Promise<SecurityFsConfigOut> {
    return this.request<SecurityFsConfigOut>('/security/fs-config');
  }

  /** PUT /api/v1/security/fs-config — replace the file-system isolation config. */
  async updateSecurityFsConfig(payload: SecurityFsConfigRequest): Promise<{ status: string }> {
    return this.request('/security/fs-config', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  /** GET /api/v1/security/network-allowlist — allowed domains and scoping mode. */
  async getNetworkAllowlist(): Promise<NetworkAllowlistOut> {
    return this.request<NetworkAllowlistOut>('/security/network-allowlist');
  }

  /** PUT /api/v1/security/network-allowlist/policy — toggle strict domain mode. */
  async updateNetworkAllowlistPolicy(strictDomainMode: boolean): Promise<NetworkAllowlistOut & { status: string }> {
    return this.request('/security/network-allowlist/policy', {
      method: 'PUT',
      body: JSON.stringify({ strict_domain_mode: strictDomainMode }),
    });
  }

  /** POST /api/v1/security/network-allowlist — add one domain. */
  async addNetworkAllowlistDomain(domain: string): Promise<NetworkAllowlistOut & { status: string; domain: string }> {
    return this.request('/security/network-allowlist', {
      method: 'POST',
      body: JSON.stringify({ domain }),
    });
  }

  /** DELETE /api/v1/security/network-allowlist/{domain} — remove one domain. */
  async removeNetworkAllowlistDomain(domain: string): Promise<NetworkAllowlistOut & { status: string; domain: string }> {
    return this.request(`/security/network-allowlist/${encodeURIComponent(domain)}`, { method: 'DELETE' });
  }

  // Prompt Templates
  /** GET /api/v1/prompt-templates — list with optional tag/model/builtin filters. */
  async listPromptTemplates(params?: { tag?: string; model_id?: string; builtin_only?: boolean; custom_only?: boolean }): Promise<PromptTemplateOut[]> {
    const search = new URLSearchParams();
    if (params?.tag) search.set('tag', params.tag);
    if (params?.model_id) search.set('model_id', params.model_id);
    if (params?.builtin_only) search.set('builtin_only', 'true');
    if (params?.custom_only) search.set('custom_only', 'true');
    const qs = search.size > 0 ? `?${search.toString()}` : '';
    return this.request<PromptTemplateOut[]>(`/prompt-templates${qs}`);
  }

  /** POST /api/v1/prompt-templates — create a custom template. */
  async createPromptTemplate(data: PromptTemplateInput): Promise<PromptTemplateOut> {
    return this.request<PromptTemplateOut>('/prompt-templates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** GET /api/v1/prompt-templates/{id} — fetch one template. */
  async getPromptTemplate(id: string): Promise<PromptTemplateOut> {
    return this.request<PromptTemplateOut>(`/prompt-templates/${encodeURIComponent(id)}`);
  }

  /** PUT /api/v1/prompt-templates/{id} — update a custom template. */
  async updatePromptTemplate(id: string, data: Partial<PromptTemplateInput>): Promise<PromptTemplateOut> {
    return this.request<PromptTemplateOut>(`/prompt-templates/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /** DELETE /api/v1/prompt-templates/{id} — delete a custom template. */
  async deletePromptTemplate(id: string): Promise<{ status: string; id: string }> {
    return this.request<{ status: string; id: string }>(`/prompt-templates/${encodeURIComponent(id)}`, { method: 'DELETE' });
  }

  /** POST /api/v1/prompt-templates/{id}/duplicate — copy a template. */
  async duplicatePromptTemplate(id: string, name?: string): Promise<PromptTemplateOut> {
    return this.request<PromptTemplateOut>(`/prompt-templates/${encodeURIComponent(id)}/duplicate`, {
      method: 'POST',
      body: JSON.stringify(name ? { name } : {}),
    });
  }

  /** POST /api/v1/prompt-templates/{id}/render — render with variable substitution. */
  async renderPromptTemplate(id: string, variables?: Record<string, string>): Promise<{ rendered: string; template_id: string }> {
    return this.request<{ rendered: string; template_id: string }>(`/prompt-templates/${encodeURIComponent(id)}/render`, {
      method: 'POST',
      body: JSON.stringify(variables ? { variables } : {}),
    });
  }

  /** POST /api/v1/prompt-templates/import — import a single template from JSON. */
  async importPromptTemplate(json: string): Promise<{ status: string; template: PromptTemplateOut }> {
    return this.request<{ status: string; template: PromptTemplateOut }>('/prompt-templates/import', {
      method: 'POST',
      body: JSON.stringify({ json }),
    });
  }

  /** POST /api/v1/prompt-templates/import-bulk — import a JSON array of templates. */
  async importPromptTemplatesBulk(json: string): Promise<{ status: string; count: number; templates: PromptTemplateOut[] }> {
    return this.request<{ status: string; count: number; templates: PromptTemplateOut[] }>('/prompt-templates/import-bulk', {
      method: 'POST',
      body: JSON.stringify({ json }),
    });
  }

  /** GET /api/v1/prompt-templates/{id}/export — export one template as JSON. */
  async exportPromptTemplate(id: string): Promise<{ json: string }> {
    return this.request<{ json: string }>(`/prompt-templates/${encodeURIComponent(id)}/export`);
  }

  /** GET /api/v1/prompt-templates/export-all — export all custom templates as JSON. */
  async exportAllPromptTemplates(): Promise<{ json: string }> {
    return this.request<{ json: string }>('/prompt-templates/export-all');
  }

  // Research
  /** POST /api/v1/research — zero-key web research pipeline (backend routes/research.py). */
  async runResearch(data: { query: string; sources?: number; timeout_s?: number }): Promise<{
    ok: boolean;
    query: string;
    summary: string;
    findings: Array<{ source: string; title: string; key_points: string[]; rel_score: number }>;
    sources: string[];
    generated_at: string;
  }> {
    return this.request('/research', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Observability — audit chain, alignment, emergency stop (app/core/observability/api.py)
  /** GET /api/v1/observability/audit — hash-chained decision audit entries. */
  async getObservabilityAudit(options?: { limit?: number; offset?: number; decisionType?: string; sessionId?: string }) {
    const params = new URLSearchParams();
    if (options?.limit) params.set('limit', String(options.limit));
    if (options?.offset) params.set('offset', String(options.offset));
    if (options?.decisionType) params.set('decision_type', options.decisionType);
    if (options?.sessionId) params.set('session_id', options.sessionId);
    const query = params.toString();
    return this.request<{
      entries: Array<Record<string, unknown>>;
      total: number;
      limit: number;
      offset: number;
    }>(`/observability/audit${query ? `?${query}` : ''}`);
  }

  /** GET /api/v1/observability/alignment — goal tracker state and drift score. */
  async getAlignmentStatus(): Promise<{
    goals: Array<Record<string, unknown>>;
    drift_score: number;
    threshold: number;
  }> {
    return this.request('/observability/alignment');
  }

  /** GET /api/v1/observability/emergency-stop — current kill-switch state. */
  async getEmergencyStopStatus(): Promise<Record<string, unknown>> {
    return this.request('/observability/emergency-stop');
  }

  /** POST /api/v1/observability/emergency-stop — activate the kill switch. */
  async activateEmergencyStop(data: { reason: string; triggered_by?: string }) {
    return this.request<{ status: string; record: Record<string, unknown> }>('/observability/emergency-stop', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** DELETE /api/v1/observability/emergency-stop — deactivate the kill switch. */
  async deactivateEmergencyStop(data?: { reason?: string; triggered_by?: string }) {
    return this.request<{ status: string; record: Record<string, unknown> }>('/observability/emergency-stop', {
      method: 'DELETE',
      body: JSON.stringify(data ?? {}),
    });
  }

}

export const api = new ApiClient();
