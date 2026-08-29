import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../api';
import type { ChatMessage, ChatToolCall } from '../types/message';

export type { ChatMessage } from '../types/message';

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const activeAssistantIdRef = useRef<string | null>(null);
  const isStreamingRef = useRef(false);
  const mountedRef = useRef(true);
  const sessionVersionRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      if (abortRef.current) {
        abortRef.current();
        abortRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const version = ++sessionVersionRef.current;
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    isStreamingRef.current = false;
    setIsStreaming(false);
    setError(null);
    if (!sessionId) {
      setMessages([]);
      return;
    }

    setMessages([]);

    api.getSessionMessages(sessionId).then((data) => {
      if (!mountedRef.current || version !== sessionVersionRef.current || isStreamingRef.current) return;
      const msgs: ChatMessage[] = (data.messages || []).map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content || '',
        toolCalls: Array.isArray(m.toolCalls) ? m.toolCalls : [],
        tool_name: m.tool_name,
        timestamp: (() => { const d = m.created_at ? new Date(m.created_at) : new Date(); return isNaN(d.getTime()) ? new Date() : d; })(),
      }));
      setMessages(msgs);
    }).catch(() => {
      if (mountedRef.current && version === sessionVersionRef.current) {
        setMessages([]);
      }
    });
  }, [sessionId]);

  const failRunningToolCalls = useCallback((assistantId: string | null, message: string) => {
    if (!assistantId) return;
    setMessages(prev => prev.map(msg => {
      if (msg.id !== assistantId || !msg.toolCalls) return msg;
      return {
        ...msg,
        toolCalls: msg.toolCalls.map(tc => tc.status === 'running'
          ? { ...tc, status: 'error' as const, error: message }
          : tc),
      };
    }));
  }, []);

  const sendMessage = useCallback(async (content: string, model?: { provider?: string; modelId?: string }) => {
    if (!sessionId || isStreamingRef.current) return;
    isStreamingRef.current = true;
    setIsStreaming(true);

    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);

    const assistantId = `assistant-${Date.now()}`;
    activeAssistantIdRef.current = assistantId;
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      toolCalls: [],
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, assistantMsg]);

    const toolCallsMap = new Map<string, ChatToolCall>();

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
        const tc: ChatToolCall = {
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
        const toolId = data.tool_call_id ?? data.id;
        const existing = toolCallsMap.get(toolId);
        if (existing) {
          toolCallsMap.set(toolId, {
            ...existing,
            result: data.result ?? '',
            error: data.error ?? '',
            status: data.error ? 'error' : 'success',
          });
        }
        setMessages(prev =>
          prev.map(msg => {
            if (msg.id !== assistantId) return msg;
            return { ...msg, toolCalls: Array.from(toolCallsMap.values()) } as ChatMessage;
          })
        );
      } else if (eventType === 'done') {
        failRunningToolCalls(assistantId, 'Tool stream ended before a result was received');
        activeAssistantIdRef.current = null;
        isStreamingRef.current = false;
        setIsStreaming(false);
      } else if (eventType === 'error' || eventType === 'eof') {
        const errMsg = typeof data === 'string' ? data : (data?.detail || data?.error || 'Unknown error');
        failRunningToolCalls(
          assistantId,
          eventType === 'error' ? errMsg : 'Tool stream ended before a result was received',
        );
        if (eventType === 'error') {
          setMessages(prev => prev.map(msg => msg.id === assistantId
            ? { ...msg, content: msg.content + `\n[Error: ${errMsg}]` }
            : msg));
          setError(errMsg);
        }
        activeAssistantIdRef.current = null;
        isStreamingRef.current = false;
        setIsStreaming(false);
      }
    }, model);
  }, [failRunningToolCalls, sessionId]);

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    failRunningToolCalls(activeAssistantIdRef.current, 'Tool execution was cancelled');
    activeAssistantIdRef.current = null;
    isStreamingRef.current = false;
    setIsStreaming(false);
  }, [failRunningToolCalls]);

  const clear = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    activeAssistantIdRef.current = null;
    isStreamingRef.current = false;
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isStreaming, error, sendMessage, stopStreaming, clear };
}
