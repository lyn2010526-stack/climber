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
  const [refreshKey, setRefreshKey] = useState(0);
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let active = true;
    if (!sessionId) {
      setMessages([]);
      return;
    }
    setMessages([]);

    api.getSessionMessages(sessionId).then((data) => {
      if (!active) return;
      const msgs: Message[] = data.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content || '',
        toolCalls: m.tool_calls.map(toolCall => ({
          id: toolCall.id,
          name: toolCall.function?.name || toolCall.name || 'unknown',
          arguments: typeof toolCall.function?.arguments === 'string'
            ? JSON.parse(toolCall.function.arguments || '{}')
            : toolCall.function?.arguments || toolCall.arguments || {},
        })),
        tool_name: m.tool_name || undefined,
        timestamp: new Date(m.created_at),
      }));
      setMessages(msgs);
    }).catch(() => {
      if (active) setMessages([]);
    });

    return () => { active = false; };
  }, [sessionId, refreshKey]);

  const sendMessage = useCallback(async (content: string) => {
    if (!sessionId || isStreaming) return;

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
        const doneMessageId = data?.message_id as string | undefined;
        setMessages(prev =>
          prev.map(msg => {
            if (msg.id !== assistantId) return msg;
            const updatedToolCalls = msg.toolCalls
              ? msg.toolCalls.map(tc => ({ ...tc, status: 'success' as const }))
              : undefined;
            return { ...msg, id: doneMessageId ?? msg.id, toolCalls: updatedToolCalls } as Message;
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

  const refresh = useCallback(() => {
    setRefreshKey((key) => key + 1);
  }, []);

  return { messages, isStreaming, error, sendMessage, stopStreaming, clear, refresh };
}
