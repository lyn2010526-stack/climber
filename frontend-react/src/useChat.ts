import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from './api';

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: 'running' | 'success' | 'error';
  requiresApproval?: boolean;
  action?: string;
  description?: string;
  details?: string;
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

    abortRef.current = api.chatStream(sessionId, content, (event) => {
      switch (event.type) {
        case 'text': {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantId
                ? { ...msg, content: msg.content + event.delta }
                : msg
            )
          );
          break;
        }
        case 'thinking': {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantId
                ? { ...msg, reasoning: (msg.reasoning || '') + event.delta }
                : msg
            )
          );
          break;
        }
        case 'tool_call': {
          const tc: ToolCall = {
            id: event.toolCall.id || `tc-${Date.now()}`,
            name: event.toolCall.name,
            arguments: event.toolCall.arguments,
            status: 'running',
            requiresApproval: event.toolCall.requiresApproval,
            action: event.toolCall.action,
            description: event.toolCall.reason,
            details: event.toolCall.timeoutSeconds
              ? `Approval times out after ${event.toolCall.timeoutSeconds}s`
              : undefined,
          };
          toolCallsMap.set(tc.id, tc);
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantId
                ? { ...msg, toolCalls: Array.from(toolCallsMap.values()) }
                : msg
            )
          );
          break;
        }
        case 'tool_result': {
          setMessages(prev =>
            prev.map(msg => {
              if (msg.id !== assistantId) return msg;
              const updatedToolCalls = msg.toolCalls
                ? msg.toolCalls.map(tc =>
                    tc.id === event.toolCallId
                      ? { ...tc, result: event.result, error: event.error, status: event.error ? 'error' : 'success' }
                      : tc
                  )
                : undefined;
              return { ...msg, toolCalls: updatedToolCalls } as Message;
            })
          );
          break;
        }
        case 'done': {
          setMessages(prev =>
            prev.map(msg => {
              if (msg.id !== assistantId) return msg;
              const updatedToolCalls = msg.toolCalls
                ? msg.toolCalls.map(tc => ({ ...tc, status: 'success' as const }))
                : undefined;
              return { ...msg, id: event.messageId ?? msg.id, toolCalls: updatedToolCalls } as Message;
            })
          );
          setIsStreaming(false);
          break;
        }
        case 'error': {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantId
                ? { ...msg, content: msg.content + `\n[Error: ${event.message}]` }
                : msg
            )
          );
          setError(event.message);
          setIsStreaming(false);
          break;
        }
        case 'unknown':
          // 未识别事件保留原帧内容供排障，不中断流。
          console.warn('Unrecognized chat event', event.raw);
          break;
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
