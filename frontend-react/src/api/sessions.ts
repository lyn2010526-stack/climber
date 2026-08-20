// Sessions resource domain (including SSE chat streaming).
import type { CreateSessionResult, DeleteResult, SessionSummary, MessagesResponse } from '../types/api';
import { ApiClient, BASE_URL } from './client';

declare module './client' {
  interface ApiClient {
    listSessions(): Promise<SessionSummary[]>;
    createSession(data: any): Promise<CreateSessionResult>;
    deleteSession(id: string): Promise<DeleteResult>;
    renameSession(id: string, title: string): Promise<SessionSummary>;
    getSessionMessages(sessionId: string): Promise<MessagesResponse>;
    chatStream(
      sessionId: string,
      message: string,
      onEvent: (event: { event: string; data: any }) => void,
      model?: { provider?: string; modelId?: string },
    ): () => void;
  }
}

ApiClient.prototype.listSessions = async function (this: ApiClient): Promise<SessionSummary[]> {
  const response = await this.request<SessionSummary[] | { items: SessionSummary[] }>('/sessions');
  return Array.isArray(response) ? response : response.items;
};

ApiClient.prototype.createSession = function (this: ApiClient, data: any): Promise<CreateSessionResult> {
  return this.request<CreateSessionResult>('/sessions', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

ApiClient.prototype.deleteSession = function (this: ApiClient, id: string): Promise<DeleteResult> {
  return this.request<DeleteResult>(`/sessions/${id}`, { method: 'DELETE' });
};

ApiClient.prototype.renameSession = function (this: ApiClient, id: string, title: string): Promise<SessionSummary> {
  return this.request<SessionSummary>(`/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
};

ApiClient.prototype.getSessionMessages = function (this: ApiClient, sessionId: string): Promise<MessagesResponse> {
  return this.request<MessagesResponse>(`/sessions/${sessionId}/messages`);
};

ApiClient.prototype.chatStream = function (
  this: ApiClient,
  sessionId: string,
  message: string,
  onEvent: (event: { event: string; data: any }) => void,
  model?: { provider?: string; modelId?: string },
): () => void {
  const url = `${BASE_URL}/sessions/${sessionId}/chat`;
  const abortController = new AbortController();

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...this.getAuthHeaders() },
    body: JSON.stringify({ message, provider: model?.provider, model_id: model?.modelId }),
    signal: abortController.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
     if (!reader) {
       onEvent({ event: 'error', data: { detail: '响应流不可用' } });
       return;
     }

    const decoder = new TextDecoder();
    let buffer = '';

     while (true) {
       const { done, value } = await reader.read();
       if (done) {
         onEvent({ event: 'eof', data: null });
         break;
       }

      buffer += decoder.decode(value, { stream: true });
      if (buffer.length > 1048576) buffer = '';
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
};
