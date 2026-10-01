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
  /** 这一轮以服务端报告的失败收尾。 */
  failed?: boolean;
  /** 用户主动中断了这一轮；与 failed 互斥，不是失败。 */
  interrupted?: boolean;
  /** 随本轮用户消息发送的图片（data URL 或 http(s) URL）。 */
  images?: string[];
}

/**
 * 流式平滑参数。每帧从缓冲里释放一部分文本，而不是每个 token 触发一次
 * setState：小水滴（≤ FLUSH_MIN_CHARS 个字符）当帧全部落地，大积压按
 * 1/FLUSH_BACKLOG_DIVISOR 指数追赶，速率随积压自动加快。
 */
const FLUSH_MIN_CHARS = 2;
const FLUSH_BACKLOG_DIVISOR = 8;

let messageIdSeq = 0;
function nextId(prefix: string): string {
  messageIdSeq += 1;
  return `${prefix}-${Date.now()}-${messageIdSeq}`;
}

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const abortRef = useRef<(() => void) | null>(null);
  /** 平滑缓冲：已收到但尚未渲染到画面的文本与思考增量。 */
  const bufferRef = useRef<{ text: string; reasoning: string }>({ text: '', reasoning: '' });
  const rafRef = useRef<number | null>(null);
  /** 当前流式回合的消息 id；回合结束后置空，缓冲不再落点。 */
  const assistantIdRef = useRef<string | null>(null);

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

  /** 只把变更应用到当前流式回合的消息上。 */
  const applyTurn = useCallback((mutate: (msg: Message) => Message) => {
    const id = assistantIdRef.current;
    if (!id) return;
    setMessages(prev => prev.map(msg => (msg.id === id ? mutate(msg) : msg)));
  }, []);

  /** 取消未执行的帧刷新，并把缓冲里的全部内容一次性落地。 */
  const flushNow = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    const { text, reasoning } = bufferRef.current;
    if (!text && !reasoning) return;
    bufferRef.current = { text: '', reasoning: '' };
    applyTurn(msg => ({
      ...msg,
      content: msg.content + text,
      reasoning: (msg.reasoning || '') + reasoning,
    }));
  }, [applyTurn]);

  /** 每帧释放一部分缓冲：按帧批量 flush，文本以缓动速率追上真实流。 */
  const scheduleFlush = useCallback(() => {
    if (rafRef.current !== null) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      const { text, reasoning } = bufferRef.current;
      if (!text && !reasoning) return;
      const release = (chunk: string) => (
        chunk.length <= FLUSH_MIN_CHARS
          ? chunk
          : chunk.slice(0, Math.max(FLUSH_MIN_CHARS, Math.ceil(chunk.length / FLUSH_BACKLOG_DIVISOR)))
      );
      const textPart = release(text);
      const reasoningPart = release(reasoning);
      bufferRef.current = {
        text: text.slice(textPart.length),
        reasoning: reasoning.slice(reasoningPart.length),
      };
      applyTurn(msg => ({
        ...msg,
        content: msg.content + textPart,
        reasoning: (msg.reasoning || '') + reasoningPart,
      }));
      if (bufferRef.current.text || bufferRef.current.reasoning) scheduleFlush();
    });
  }, [applyTurn]);

  /**
   * 切换会话（或卸载）时中断在途流并丢弃未渲染的缓冲：排队中的帧
   * 永远落进用户刚离开的那个会话的记录里，是跨会话串数据的来源。
   * 中断是静默的（无 error 事件），所以 isStreaming 在这里一并复位。
   */
  useEffect(() => () => {
    abortRef.current?.();
    abortRef.current = null;
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    bufferRef.current = { text: '', reasoning: '' };
    assistantIdRef.current = null;
    setIsStreaming(false);
  }, [sessionId]);

  const sendMessage = useCallback(async (content: string, attachments?: string[]) => {
    if (!sessionId || isStreaming) return;

    const userMsg: Message = {
      id: nextId('user'),
      role: 'user',
      content,
      images: attachments?.length ? attachments : undefined,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);
    setError(null);

    const assistantId = nextId('assistant');
    assistantIdRef.current = assistantId;
    bufferRef.current = { text: '', reasoning: '' };
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
          bufferRef.current.text += event.delta;
          scheduleFlush();
          break;
        }
        case 'thinking': {
          bufferRef.current.reasoning += event.delta;
          scheduleFlush();
          break;
        }
        case 'tool_call': {
          const tc: ToolCall = {
            id: event.toolCall.id || nextId('tc'),
            name: event.toolCall.name,
            arguments: event.toolCall.arguments,
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
          flushNow();
          setMessages(prev =>
            prev.map(msg => {
              if (msg.id !== assistantId) return msg;
              const updatedToolCalls = msg.toolCalls
                ? msg.toolCalls.map(tc => ({ ...tc, status: 'success' as const }))
                : undefined;
              return { ...msg, id: event.messageId ?? msg.id, toolCalls: updatedToolCalls } as Message;
            })
          );
          assistantIdRef.current = null;
          setIsStreaming(false);
          break;
        }
        case 'error': {
          flushNow();
          applyTurn(msg => ({ ...msg, failed: true }));
          setError(event.message);
          setIsStreaming(false);
          break;
        }
        case 'unknown':
          // 未识别事件保留原帧内容供排障，不中断流。
          console.warn('Unrecognized chat event', event.raw);
          break;
      }
    }, { attachments });
  }, [sessionId, isStreaming, scheduleFlush, flushNow, applyTurn]);

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    // 用户主动中断：缓冲一次性落地，给这一轮打上 interrupted 标记（非失败）。
    flushNow();
    applyTurn(msg => ({ ...msg, interrupted: msg.interrupted ?? true }));
    setIsStreaming(false);
  }, [flushNow, applyTurn]);

  /** 失败重试：把最后一条用户消息作为新的一轮重新发送。 */
  const retry = useCallback(() => {
    if (!sessionId || isStreaming) return;
    const lastUser = [...messages].reverse().find(m => m.role === 'user' && m.content.trim());
    if (!lastUser) return;
    void sendMessage(lastUser.content, lastUser.images);
  }, [sessionId, isStreaming, messages, sendMessage]);

  const clear = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const refresh = useCallback(() => {
    setRefreshKey((key) => key + 1);
  }, []);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    stopStreaming,
    clear,
    refresh,
    retry,
    isLoading: isStreaming,
  };
}
