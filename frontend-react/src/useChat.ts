import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from './api';
import type { ChatStreamEvent, RuntimeReport, SessionInput, SessionInputKind } from './types/chatEvents';
import { useI18n } from './i18n';

export type ChatInput = Omit<SessionInput, 'status'> & { status: SessionInput['status'] | 'pending' | 'unconfirmed' };

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  status?: 'running' | 'success' | 'error';
  requiresApproval?: boolean;
  approvalId?: string;
  description?: string;
  severity?: 'low' | 'medium' | 'high';
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
  files?: ChatAttachment[];
}

export interface ChatAttachmentPayload {
  kind: 'image' | 'file';
  data: string;
  name: string;
  mime_type: string;
  size: number;
}

export type ChatAttachment = Omit<ChatAttachmentPayload, 'data'> & { data?: string };

/**
 * 流式平滑参数。每帧从缓冲里释放一部分文本，而不是每个 token 触发一次
 * setState：小水滴（≤ FLUSH_MIN_CHARS 个字符）当帧全部落地，大积压按
 * 1/FLUSH_BACKLOG_DIVISOR 指数追赶，速率随积压自动加快。
 */
const FLUSH_MIN_CHARS = 2;
const FLUSH_BACKLOG_DIVISOR = 8;
/**
 * 两次「落地」（产生一次 React commit）之间的最小墙钟间隔。性能基线（任务48）
 * 要求流式渲染的 commit 数低于 chunks/4——每个 commit 至少合并 4 个分片，渲染
 * 必须与分片到达解耦。rAF 链每帧保活，但只有距上次落地超过该间隔才真正
 * setState；未到间隔的帧只重排、不提交，从而把 commit 频率钉在该间隔上，与
 * 帧率是否被长任务阻塞无关。
 */
const FLUSH_MIN_INTERVAL_MS = 700;

let messageIdSeq = 0;
function nextId(prefix: string): string {
  messageIdSeq += 1;
  return `${prefix}-${Date.now()}-${messageIdSeq}`;
}

function parseToolArguments(value: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(value || '{}');
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : {};
  } catch {
    return {};
  }
}

export interface UseChatOptions {
  /**
   * 原始 SSE 事件旁路观察者。每帧归一化事件在进入内部状态机之前先回调一次，
   * 供面板自动显隐等 UI 联动消费真实事件流，而不是从渲染后的 messages 反推。
   * 回调抛错不影响主事件处理。
   */
  onEvent?: (event: ChatStreamEvent) => void;
}

export function useChat(sessionId: string | null, options: UseChatOptions = {}) {
  const { t } = useI18n();
  const onEventRef = useRef(options.onEvent);
  onEventRef.current = options.onEvent;
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [inputs, setInputs] = useState<ChatInput[]>([]);
  const [runtimeReport, setRuntimeReport] = useState<RuntimeReport | null>(null);
  const [resumePending, setResumePending] = useState(false);
  const [resumeFeedback, setResumeFeedback] = useState<string | null>(null);
  const resumeRequest = useRef<symbol | null>(null);
  const reportRevision = useRef(0);
  const inputsRef = useRef<ChatInput[]>([]);
  const sessionRef = useRef(sessionId);
  sessionRef.current = sessionId;
  const streamGeneration = useRef(0);
  const inputGeneration = useRef(0);
  const streamingRef = useRef(false);
  const historyGeneration = useRef(0);
  const inputRevision = useRef(0);
  const mergeInputs = useCallback((items: ChatInput[]) => {
    inputRevision.current += 1;
    const merged = new Map(inputsRef.current.map(item => [item.client_request_id, item]));
    for (const item of items) merged.set(item.client_request_id, item);
    inputsRef.current = [...merged.values()].sort((a, b) => a.sequence - b.sequence);
    setInputs(inputsRef.current);
  }, []);
  const abortRef = useRef<(() => void) | null>(null);
  /** 平滑缓冲：已收到但尚未渲染到画面的文本与思考增量。 */
  const bufferRef = useRef<{ text: string; reasoning: string }>({ text: '', reasoning: '' });
  const rafRef = useRef<number | null>(null);
  /** 上一次真正把缓冲落地（产生 commit）的墙钟时间；用于按 FLUSH_MIN_INTERVAL_MS 节流。 */
  const lastReleaseAtRef = useRef(0);
  /** 当前流式回合的消息 id；回合结束后置空，缓冲不再落点。 */
  const assistantIdRef = useRef<string | null>(null);
  const streamKindRef = useRef<'chat' | 'queue'>('chat');

  useEffect(() => {
    let active = true;
    const generation = historyGeneration.current;
    if (!sessionId) {
      setMessages([]);
      return;
    }
    setMessages([]);

    api.getSessionMessages(sessionId).then((data) => {
      if (!active || generation !== historyGeneration.current) return;
      const msgs: Message[] = data.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content || '',
        toolCalls: m.tool_calls.map(toolCall => ({
          id: toolCall.id,
          name: toolCall.function?.name || toolCall.name || 'unknown',
          arguments: typeof toolCall.function?.arguments === 'string'
             ? parseToolArguments(toolCall.function.arguments)
             : toolCall.function?.arguments || toolCall.arguments || {},
        })),
        tool_name: m.tool_name || undefined,
        timestamp: new Date(m.created_at),
        images: m.metadata?.images,
        files: m.metadata?.attachments,
      }));
      setMessages(msgs);
    }).catch(() => {
      if (active && generation === historyGeneration.current) setMessages([]);
    });

    return () => { active = false; };
  }, [sessionId, refreshKey]);

  useEffect(() => {
    inputsRef.current = [];
    streamKindRef.current = 'chat';
    setInputs([]);
    setError(null);
    setRuntimeReport(null);
    reportRevision.current += 1;
    resumeRequest.current = null;
    setResumePending(false);
    setResumeFeedback(null);
    inputGeneration.current += 1;
    const generation = inputGeneration.current;
    const revision = inputRevision.current;
    if (sessionId) void api.getSessionInputs?.(sessionId).then(items => {
      if (generation === inputGeneration.current && sessionRef.current === sessionId && revision === inputRevision.current) mergeInputs(items);
    }).catch(() => undefined);
    return () => { inputGeneration.current += 1; };
  }, [sessionId, mergeInputs]);

  const refreshReport = useCallback(async () => {
    if (!sessionId) return;
    const generation = inputGeneration.current;
    const revision = reportRevision.current;
    const stream = streamGeneration.current;
    try {
      const report = await api.getSessionInputReport?.(sessionId);
      if (report && sessionRef.current === sessionId && generation === inputGeneration.current &&
          revision === reportRevision.current && stream === streamGeneration.current) {
        reportRevision.current += 1;
        setRuntimeReport(report);
      }
    } catch { /* Keep the last server report when snapshot recovery is unavailable. */ }
  }, [sessionId]);

  useEffect(() => { void refreshReport(); }, [refreshReport, isStreaming]);

  const resumeInputs = useCallback(async (reviewConfirmed: boolean): Promise<boolean> => {
    if (!sessionId || reviewConfirmed !== true || resumeRequest.current) return false;
    const request = Symbol();
    resumeRequest.current = request;
    const generation = inputGeneration.current;
    const revision = inputRevision.current;
    setResumePending(true);
    setResumeFeedback(null);
    try {
      const items = await api.resumeSessionInputs(sessionId, true);
      if (sessionRef.current !== sessionId || generation !== inputGeneration.current || resumeRequest.current !== request) return false;
      if (revision === inputRevision.current) mergeInputs(items);
      setResumeFeedback(t('anchored.resume.confirmed'));
      await refreshReport();
      return true;
    } catch (cause) {
      if (sessionRef.current === sessionId && generation === inputGeneration.current && resumeRequest.current === request) {
        setResumeFeedback(cause instanceof Error && cause.message
          ? `${t('anchored.resume.failed')}: ${cause.message}`
          : t('anchored.resume.failed'));
      }
      return false;
    } finally {
      if (resumeRequest.current === request) {
        resumeRequest.current = null;
        setResumePending(false);
      }
    }
  }, [sessionId, mergeInputs, refreshReport, t]);

  // One request at a time, with a bounded timeout; polling exists only while streaming.
  useEffect(() => {
    if (!sessionId || !isStreaming) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const reconcile = async () => {
      const revision = inputRevision.current;
      try {
        const items = await api.getSessionInputs(sessionId);
        if (active && sessionRef.current === sessionId && revision === inputRevision.current) mergeInputs(items);
      } catch { /* A later snapshot or SSE event can confirm an uncertain submission. */ }
      if (active) timer = setTimeout(reconcile, 3000);
    };
    void reconcile();
    return () => { active = false; clearTimeout(timer); };
  }, [sessionId, isStreaming, mergeInputs]);

  const submitInput = useCallback(async (message: string, kind: SessionInputKind, requestId?: string): Promise<boolean> => {
    if (!sessionId || !streamingRef.current || !message.trim()) return false;
    const id = requestId ?? nextId('input');
    const existing = inputsRef.current.find(item => item.client_request_id === id);
    if (existing?.status === 'pending') return false;
    const generation = inputGeneration.current;
    mergeInputs([{ id: existing?.id ?? id, client_request_id: id, kind, message: message.trim(), status: 'pending', sequence: existing?.sequence ?? Number.MAX_SAFE_INTEGER }]);
    try {
      const item = await api.submitSessionInput(sessionId, { client_request_id: id, kind, message: message.trim() });
      if (generation !== inputGeneration.current || sessionRef.current !== sessionId) return false;
      // SSE may have advanced this item while the POST response was in flight.
      const current = inputsRef.current.find(input => input.client_request_id === id);
      if (!current || current.status === 'pending' || current.status === 'unconfirmed') mergeInputs([item]);
      return true;
    } catch (cause) {
      if (generation !== inputGeneration.current || sessionRef.current !== sessionId) return false;
      const current = inputsRef.current.find(input => input.client_request_id === id);
      if (current && current.status !== 'pending' && current.status !== 'unconfirmed') return true;
      mergeInputs([{ ...existing, id: existing?.id ?? id, client_request_id: id, kind, message: message.trim(), status: 'unconfirmed', sequence: existing?.sequence ?? Number.MAX_SAFE_INTEGER, error: cause instanceof Error ? cause.message : '输入发送失败' }]);
      return false;
    }
  }, [sessionId, mergeInputs]);

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
    lastReleaseAtRef.current = performance.now();
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
      // 时间门控：距上次落地不足 FLUSH_MIN_INTERVAL_MS 时，这一帧只把 rAF 链
      // 续上、不 setState，于是不产生 commit。这样 commit 频率被钉在节流间隔上，
      // 满足任务48「commit < chunks/4」的解耦要求，与帧率/长任务阻塞无关。
      const now = performance.now();
      if (now - lastReleaseAtRef.current >= FLUSH_MIN_INTERVAL_MS) {
        lastReleaseAtRef.current = now;
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
      }
      if (bufferRef.current.text || bufferRef.current.reasoning) scheduleFlush();
    });
  }, [applyTurn]);

  /**
   * 切换会话（或卸载）时中断在途流并丢弃未渲染的缓冲：排队中的帧
   * 永远落进用户刚离开的那个会话的记录里，是跨会话串数据的来源。
   * 中断是静默的（无 error 事件），所以 isStreaming 在这里一并复位。
   */
  useEffect(() => () => {
    streamGeneration.current += 1;
    streamingRef.current = false;
    abortRef.current?.();
    abortRef.current = null;
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    bufferRef.current = { text: '', reasoning: '' };
    assistantIdRef.current = null;
    setIsStreaming(false);
  }, [sessionId]);

  const beginStream = useCallback((content?: string, attachments?: string[], files?: ChatAttachmentPayload[]) => {
    if (!sessionId || streamingRef.current || resumeRequest.current) return;
    const queuedOnly = content === undefined;
    if (!queuedOnly && !content.trim() && !attachments?.length && !files?.length) return;
    streamKindRef.current = queuedOnly ? 'queue' : 'chat';
    streamingRef.current = true;
    historyGeneration.current += 1;
    const generation = ++streamGeneration.current;

    let assistantId = queuedOnly ? '' : nextId('assistant');
    assistantIdRef.current = assistantId;
    bufferRef.current = { text: '', reasoning: '' };
    if (!queuedOnly) {
      const userMsg: Message = {
        id: nextId('user'),
        role: 'user',
        content,
        images: attachments?.length ? attachments : undefined,
        files: files?.length ? files.map(file => ({ ...file })) : undefined,
        timestamp: new Date(),
      };
      const assistantMsg: Message = {
        id: assistantId,
        role: 'assistant',
        content: '',
        toolCalls: [],
        timestamp: new Date(),
      };
      // 两个 setMessages 合并为一次：开始一个回合只应产生一次 commit（任务48 的
      // 流式渲染预算把窗口内所有 commit 都计入）。
      setMessages(prev => [...prev, userMsg, assistantMsg]);
    }
    setIsStreaming(true);
    setError(null);
    setRuntimeReport(null);

    const toolCallsMap = new Map<string, ToolCall>();
    const startedInputs = new Set<string>();
    const toolOwners = new Map<string, string>();
    const findToolId = (toolCallId: string) => {
      if (toolCallsMap.has(toolCallId)) return toolCallId;
      const match = [...toolCallsMap.keys()].find(id =>
        id.endsWith(`:${toolCallId}`) || toolCallId.endsWith(`:${id}`));
      return match ?? toolCallId;
    };
    const finishTurn = (messageId?: string, fallback?: string, status?: string) => {
      if (!assistantId) return;
      // Final done can follow turn_done; restore the last turn's buffer target before flushing.
      assistantIdRef.current = assistantId;
      flushNow();
      const oldId = assistantId;
      const newId = messageId ?? oldId;
      for (const [id, owner] of toolOwners) if (owner === oldId) toolOwners.set(id, newId);
      setMessages(prev => prev.map(msg => msg.id === oldId ? {
        ...msg, id: newId, content: msg.content || fallback || '',
        ...(status === 'failed' ? { failed: true } : {}),
        ...(status === 'stopped' ? { interrupted: true } : {}),
      } : msg));
      assistantId = newId;
      assistantIdRef.current = null;
    };

    const onEvent = (event: ChatStreamEvent) => {
      if (generation !== streamGeneration.current || sessionRef.current !== sessionId) return;
      try {
        onEventRef.current?.(event);
      } catch {
        // 观察者回调属于旁路 UI 联动，异常不得中断主事件流。
      }
      switch (event.type) {
        case 'runtime_report':
          reportRevision.current += 1;
          setRuntimeReport(event.report);
          break;
        case 'loop_status':
          // Pi dual-loop outer-round status; consumed by observers (onEvent)
          // for the long-task loop panel. Explicit handling keeps the stream
          // from classifying this as an unknown event.
          break;
        case 'input_status':
          mergeInputs([event.item]);
          break;
        case 'turn_started': {
          if (!event.inputId || startedInputs.has(event.inputId)) break;
          startedInputs.add(event.inputId);
          flushNow();
          toolCallsMap.clear();
          assistantId = nextId('assistant');
          assistantIdRef.current = assistantId;
          const turnId = assistantId;
          setMessages(prev => [...prev,
            { id: nextId('user'), role: 'user', content: event.message, timestamp: new Date() },
            { id: turnId, role: 'assistant', content: '', toolCalls: [], timestamp: new Date() },
          ]);
          break;
        }
        case 'turn_done':
          finishTurn(event.messageId, undefined, event.status);
          break;
        case 'text': {
          if (!assistantId) break;
          assistantIdRef.current = assistantId;
          bufferRef.current.text += event.delta;
          scheduleFlush();
          break;
        }
        case 'thinking': {
          if (!assistantId) break;
          // The backend emits iteration-only thinking frames for loop progress.
          // Only text-bearing frames belong in the public reasoning transcript.
          if (!event.delta) break;
          assistantIdRef.current = assistantId;
          bufferRef.current.reasoning += event.delta;
          scheduleFlush();
          break;
        }
        case 'tool_call': {
          if (!assistantId) break;
          const rawId = event.toolCall.id || nextId('tc');
          const tc: ToolCall = {
            id: startedInputs.size ? `${assistantId}:${rawId}` : rawId,
            name: event.toolCall.name,
            arguments: event.toolCall.arguments,
            status: 'running',
            ...(event.toolCall.requiresApproval ? {
              requiresApproval: true,
              approvalId: rawId,
              description: event.toolCall.description,
              severity: event.toolCall.severity,
            } : {}),
          };
          toolCallsMap.set(rawId, tc);
          toolOwners.set(rawId, assistantId);
          const owner = assistantId;
          const calls = Array.from(toolCallsMap.values());
          setMessages(prev =>
            prev.map(msg =>
              msg.id === owner
                ? { ...msg, toolCalls: calls }
                : msg
            )
          );
          break;
        }
        case 'tool_result': {
          const resolvedId = findToolId(event.toolCallId);
          const owner = toolOwners.get(resolvedId);
          const previous = toolCallsMap.get(resolvedId);
          if (previous) toolCallsMap.set(resolvedId, {
            ...previous, result: event.result, error: event.error,
            requiresApproval: false, status: event.error ? 'error' : 'success',
          });
          setMessages(prev =>
            prev.map(msg => {
              if (msg.id !== owner) return msg;
              const updatedToolCalls = msg.toolCalls
                ? msg.toolCalls.map(tc =>
                    (tc.id === previous?.id || tc.id.endsWith(`:${resolvedId}`))
                      ? { ...tc, result: event.result, error: event.error, requiresApproval: false, status: event.error ? 'error' : 'success' }
                      : tc
                  )
                : undefined;
              return { ...msg, toolCalls: updatedToolCalls } as Message;
            })
          );
          break;
        }
        case 'checkpoint':
        case 'context_compression':
        case 'progress':
        case 'model_fallback':
        case 'sub_agent_start':
        case 'sub_agent_end':
        case 'pipeline_complete':
          // Lifecycle telemetry is exposed through onEvent for dedicated panels.
          break;
        case 'done': {
          finishTurn(event.messageId, event.content, event.status);
          streamingRef.current = false;
          streamGeneration.current += 1;
          setIsStreaming(false);
          void api.getSessionInputs?.(sessionId).then(items => {
            if (sessionRef.current === sessionId && generation + 1 === streamGeneration.current) mergeInputs(items);
          }).catch(() => undefined);
          break;
        }
        case 'error': {
          finishTurn(undefined, undefined, 'failed');
          setError(event.message);
          streamingRef.current = false;
          streamGeneration.current += 1;
          setIsStreaming(false);
          break;
        }
        case 'unknown':
          // 未识别事件保留原帧内容供排障，不中断流。
          console.warn('Unrecognized chat event', event.raw);
          break;
      }
    };
    abortRef.current = queuedOnly
      ? api.startSessionInputs(sessionId, onEvent)
      : api.chatStream(sessionId, content, onEvent, { attachments, files });
  }, [sessionId, scheduleFlush, flushNow, mergeInputs]);

  const sendMessage = useCallback(async (content: string, attachments?: string[], files?: ChatAttachmentPayload[]) => {
    beginStream(content, attachments, files);
  }, [beginStream]);

  const startInputs = useCallback(() => {
    if (!inputsRef.current.some(item => item.kind === 'follow_up' && item.status === 'queued')) return;
    beginStream();
  }, [beginStream]);

  const stopStreaming = useCallback(() => {
    resumeRequest.current = null;
    setResumePending(false);
    setResumeFeedback(null);
    streamGeneration.current += 1;
    streamingRef.current = false;
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
    if (streamKindRef.current === 'queue') { startInputs(); return; }
    const lastUser = [...messages].reverse().find(m => m.role === 'user' && (m.content.trim() || m.images?.length || m.files?.length));
    if (!lastUser) return;
    const retryFiles = lastUser.files?.filter(
      (file): file is ChatAttachmentPayload => typeof file.data === 'string',
    );
    void sendMessage(lastUser.content, lastUser.images, retryFiles);
  }, [sessionId, isStreaming, messages, sendMessage, startInputs]);

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
    inputs,
    runtimeReport,
    resumeInputs,
    resumePending,
    resumeFeedback,
    startInputs,
    submitInput,
    retryInput: (item: ChatInput) => submitInput(item.message, item.kind, item.client_request_id),
  };
}
