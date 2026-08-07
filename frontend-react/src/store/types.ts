// ── Centralized Type Definitions ──

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

export interface Session {
  id: string;
  title: string;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error';
  messages: Message[];
  activeSkills: string[];
  activeTools: string[];
  modelConfig: {
    provider: string;
    modelId: string;
    temperature: number;
    maxTokens: number;
  };
  tokenUsage: {
    used: number;
    limit: number;
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
export type PermissionMode = 'sandbox' | 'native';
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
