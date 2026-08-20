// Unified message type definitions.
// ChatMessage: chat protocol message used by useChat / ChatInterface.
// DisplayMessage: presentation-layer message used by the workspace store.

export interface ChatToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: 'running' | 'success' | 'error';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: ChatToolCall[];
  tool_name?: string;
  reasoning?: string;
  timestamp?: Date;
}

export interface DisplayMessageMetadata {
  tokens?: number;
  durationMs?: number;
  status?: 'pending' | 'running' | 'success' | 'error' | 'cancelled';
  retryCount?: number;
  blockReason?: string;
  toolName?: string;
  toolArgs?: any;
}

export interface DisplayMessage {
  id: string;
  type: 'user' | 'thinking' | 'tool-call' | 'tool-result' | 'reflection' | 'system';
  content: any;
  timestamp: number;
  metadata?: DisplayMessageMetadata;
}
