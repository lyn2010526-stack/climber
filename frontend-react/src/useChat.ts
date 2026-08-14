import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from './api';

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: 'running' | 'success' | 'error';
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
  tool_name?: string;
  reasoning?: string;
  timestamp?: Date;
}

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    // 立即清空，消除切换闪烁
    setMessages([]);

    api.getSessionMessages(sessionId).then((data: any) => {
      const msgs: Message[] = (data.messages || []).map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content || '',
        toolCalls: Array.isArray(m.toolCalls) ? m.toolCalls : [],
        tool_name: m.tool_name,
        timestamp: (() => { const d = m.created_at ? new Date(m.created_at) : new Date(); return isNaN(d.getTime()) ? new Date() : d; })(),
      }));
      setMessages(msgs);
    }).catch(() => {
      setMessages([]);
    });
  }, [sessionId]);

  const sendMessage = useCallback(async (content: string) => {
    if (!sessionId || isStreaming) return;

    // 先中止上一个 stream
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);
    setError(null);

    const assistantId = `assistant-${Date.now()}`;
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      toolCalls: [],
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, assistantMsg]);

    const toolCallsMap = new Map<string, ToolCall>();

    abortRef.current = api.chatStream(sessionId, content, (event: any) => {
      const eventType = event.event;
      const data = event.data;

      if (eventType === 'text') {
        const delta = typeof data === 'string' ? data : (data?.content || '');
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantId
              ? { ...msg, content: msg.content + delta }
              : msg
          )
        );
      } else if (eventType === 'thinking') {
        const thinking = typeof data === 'string' ? data : (data?.content || '');
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantId
              ? { ...msg, reasoning: (msg.reasoning || '') + thinking }
              : msg
          )
        );
      } else if (eventType === 'tool_call') {
        const tc: ToolCall = {
          id: data.id || `tc-${Date.now()}`,
          name: data.name || 'unknown',
          arguments: data.arguments || {},
          status: 'running',
        };
        toolCallsMap.set(tc.id, tc);
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantId
              ? { ...msg, toolCalls: Array.from(toolCallsMap.values()) }
              : msg
          )
        );
      } else if (eventType === 'tool_result') {
        const toolId = data.id;
        setMessages(prev =>
          prev.map(msg => {
            if (msg.id !== assistantId) return msg;
            const updatedToolCalls = msg.toolCalls
              ? msg.toolCalls.map(tc =>
                  tc.id === toolId
                    ? { ...tc, result: data.result ?? '', error: data.error ?? '', status: data.error ? 'error' : 'success' }
                    : tc
                )
              : undefined;
            return { ...msg, toolCalls: updatedToolCalls } as Message;
          })
        );
      } else if (eventType === 'done') {
        setMessages(prev =>
          prev.map(msg => {
            if (msg.id !== assistantId) return msg;
            const updatedToolCalls = msg.toolCalls
              ? msg.toolCalls.map(tc => ({ ...tc, status: 'success' as const }))
              : undefined;
            return { ...msg, toolCalls: updatedToolCalls } as Message;
          })
        );
        setIsStreaming(false);
      } else if (eventType === 'error') {
        const errMsg = typeof data === 'string' ? data : (data?.detail || data?.error || 'Unknown error');
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantId
              ? { ...msg, content: msg.content + `\n[Error: ${errMsg}]` }
              : msg
          )
        );
        setError(errMsg);
        setIsStreaming(false);
      }
    });
  }, [sessionId, isStreaming]);

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isStreaming, error, sendMessage, stopStreaming, clear };
}
