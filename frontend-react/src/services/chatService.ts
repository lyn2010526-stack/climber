import { apiClient } from '../lib/api-client';

export interface ChatSession {
  id: string;
  title: string | null;
  status: string;
  agent_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: ToolCall[];
  tool_name?: string;
  created_at: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: string;
}

export interface SendMessageRequest {
  message: string;
  session_id?: string;
  agent_id?: string;
}

export interface StreamEvent {
  event: 'text' | 'thinking' | 'tool_call' | 'tool_result' | 'done' | 'error';
  data: unknown;
}

export type StreamCallback = (event: StreamEvent) => void;

export const chatService = {
  async listSessions(): Promise<ChatSession[]> {
    return apiClient.get<ChatSession[]>('/api/chat/sessions');
  },

  async getSession(sessionId: string): Promise<ChatSession> {
    return apiClient.get<ChatSession>(`/api/chat/sessions/${sessionId}`);
  },

  async createSession(data?: { title?: string; agent_id?: string }): Promise<ChatSession> {
    return apiClient.post<ChatSession>('/api/chat/sessions', data || {});
  },

  async deleteSession(sessionId: string): Promise<void> {
    await apiClient.delete<void>(`/api/chat/sessions/${sessionId}`);
  },

  async getMessages(sessionId: string): Promise<ChatMessage[]> {
    return apiClient.get<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`);
  },

  async sendMessage(data: SendMessageRequest): Promise<ChatMessage> {
    return apiClient.post<ChatMessage>('/api/chat/messages', data);
  },

  chatStream(
    sessionId: string,
    content: string,
    onEvent: StreamCallback,
    options?: { agent_id?: string }
  ): () => void {
    const controller = new AbortController();

    const doStream = async () => {
      try {
        const res = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, message: content, ...options }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          onEvent({ event: 'error', data: { detail: `HTTP ${res.status}` } });
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;
            if (!line.startsWith('data: ')) continue;

            const raw = line.slice(6);
            if (raw === '[DONE]') {
              onEvent({ event: 'done', data: null });
              continue;
            }

            try {
              const parsed = JSON.parse(raw);
              onEvent(parsed);
            } catch {
              onEvent({ event: 'text', data: raw });
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          onEvent({ event: 'error', data: { detail: (err as Error).message } });
        }
      }
    };

    doStream();
    return () => controller.abort();
  },
};