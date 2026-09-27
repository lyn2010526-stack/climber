export interface Message {
  id: string;
  type: 'user' | 'thinking' | 'tool-call' | 'tool-result' | 'reflection' | 'system';
  content: any;
  timestamp: number;
  metadata?: {
    tokens?: number;
    durationMs?: number;
    status?: 'pending' | 'running' | 'success' | 'error' | 'cancelled';
    retryCount?: number;
    blockReason?: string;
    toolName?: string;
    toolArgs?: any;
  };
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
  tool_name?: string;
  reasoning?: string;
  timestamp?: Date;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: 'running' | 'success' | 'error';
}

/**
 * Session status vocabulary. The backend owns the values (`app/core/__init__.py`
 * `SessionStatus` plus the `idle`/`pending` strings the sessions API stores);
 * `unknown` is the only frontend-invented state and marks an unreported value.
 */
export type SessionStatus =
  | 'pending'
  | 'idle'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'stopped'
  | 'unknown';

export interface Session {
  id: string;
  title: string;
  status: SessionStatus;
  messages: Message[];
  activeSkills: string[];
  activeTools: string[];
  /** Absent until a payload reports it; never defaulted to a real-looking value. */
  modelConfig?: {
    provider?: string;
    modelId?: string;
    temperature?: number;
    maxTokens?: number;
  };
  tokenUsage?: {
    used?: number;
    limit?: number;
  };
  createdAt: number;
}

export interface TaskItem {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export interface Snapshot {
  id: string;
  sessionId: string;
  timestamp: number;
  label: string;
}

export type RightPanelTab = 'config' | 'diff' | 'toolcalls' | 'dag' | 'trace' | 'reasoning' | 'files';
/** Mirrors `app/core/permission_rules.py:PermissionMode`, the backend vocabulary. */
export type PermissionMode = 'default' | 'acceptEdits' | 'plan' | 'auto' | 'bypass' | 'strict';
export type Theme = 'dark' | 'light';

export interface AuthUser {
  id: string;
  name: string;
  email?: string;
  role?: string;
  avatar_url?: string;
}

export type Page =
  | 'chat' | 'agents' | 'workflows' | 'crews' | 'apikeys' | 'skills'
  | 'notifications' | 'doctor' | 'mcp' | 'stats' | 'factory' | 'plugins'
  | 'plugin-manage' | 'scheduler' | 'cluster' | 'traces' | 'eval' | 'cost'
  | 'settings' | 'tasks' | 'task-history' | 'reasoning' | 'reasoning-history'
  | 'terminal' | 'memory';

export interface CollabEvent {
  type: string;
  session_id: string;
  member_id?: string;
  member_name?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

export interface ApprovalQueueItem {
  id: string;
  command: string;
  riskLevel: 'low' | 'medium' | 'high';
  timestamp: number;
}
