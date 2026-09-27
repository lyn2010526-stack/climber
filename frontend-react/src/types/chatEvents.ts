/**
 * SSE 事件契约。
 *
 * 传输层保持后端现有的 `event:` + `data:` 形态，`ChatStreamEvent` 是前端内部
 * 归一化后的判别联合。`RawSSEEvent` 保留线上原始形态，供适配器与排障使用。
 *
 * AG-UI 约定事件类型位于 JSON `data.type` 而非 `event:` 行。本项目的后端目前
 * 走 `event:` 行，适配器同时接受两种来源：读到 `data.type` 时以其为准。
 */

/** 后端线上实际发出的事件名。 */
export const CHAT_EVENT = {
  TEXT: 'text',
  THINKING: 'thinking',
  TOOL_CALL: 'tool_call',
  TOOL_RESULT: 'tool_result',
  DONE: 'done',
  ERROR: 'error',
} as const;

export type ChatEventName = (typeof CHAT_EVENT)[keyof typeof CHAT_EVENT];

/** 传输层原始帧：未经解析与归一化。 */
export interface RawSSEEvent {
  /** `event:` 行的值；后端未指定时为空串。 */
  event: string;
  /** 已 JSON.parse 的负载；解析失败时为原始字符串。 */
  data: unknown;
}

/** AG-UI 风格的负载：以 `type` 字段指明事件种类。 */
export interface AgUiEventPayload {
  type: string;
  [key: string]: unknown;
}

export interface ToolCallPayload {
  id?: string;
  name?: string;
  arguments?: Record<string, unknown>;
  result?: string;
  error?: string;
  tool_name?: string;
  content?: string;
}

export interface ErrorPayload {
  detail?: string;
  error?: string;
  message?: string;
}

export interface DonePayload {
  message_id?: string;
}

export type ChatStreamEvent =
  | { type: 'text'; delta: string }
  | { type: 'thinking'; delta: string }
  | {
      type: 'tool_call';
      toolCall: { id: string; name: string; arguments: Record<string, unknown> };
    }
  | { type: 'tool_result'; toolCallId: string; result: string; error: string }
  | { type: 'done'; messageId?: string }
  | { type: 'error'; message: string }
  | { type: 'unknown'; raw: RawSSEEvent };

/** 把任意 `data` 负载安全地视作对象。 */
function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'string' && value.length > 0) return value;
  }
  return '';
}

/**
 * 把一帧原始 SSE 归一化为 `ChatStreamEvent`。
 *
 * 事件名优先取 `data.type`（AG-UI 形态），其次取 `event:` 行（当前后端形态）。
 * 两种来源都缺失时归类为 `unknown`，调用方可据此记录原始帧而不中断流。
 */
export function normalizeChatEvent(raw: RawSSEEvent): ChatStreamEvent {
  const payload = asRecord(raw.data);
  const name = (typeof payload.type === 'string' && payload.type) || raw.event;

  switch (name) {
    case CHAT_EVENT.TEXT: {
      const delta = readString(payload, ['content', 'delta', 'text']);
      return { type: 'text', delta: typeof raw.data === 'string' ? raw.data : delta };
    }
    case CHAT_EVENT.THINKING: {
      const delta = readString(payload, ['content', 'delta', 'text', 'reasoning']);
      return { type: 'thinking', delta: typeof raw.data === 'string' ? raw.data : delta };
    }
    case CHAT_EVENT.TOOL_CALL: {
      return {
        type: 'tool_call',
        toolCall: {
          id: readString(payload, ['id', 'tool_call_id', 'toolCallId']) || '',
          name: readString(payload, ['name', 'tool_name']) || 'unknown',
          arguments: asRecord(payload.arguments ?? payload.args ?? payload.input),
        },
      };
    }
    case CHAT_EVENT.TOOL_RESULT: {
      return {
        type: 'tool_result',
        toolCallId: readString(payload, ['id', 'tool_call_id', 'toolCallId']),
        result: readString(payload, ['result', 'output', 'content']),
        error: readString(payload, ['error', 'error_message']),
      };
    }
    case CHAT_EVENT.DONE: {
      const messageId = readString(payload, ['message_id', 'messageId', 'id']);
      return { type: 'done', messageId: messageId || undefined };
    }
    case CHAT_EVENT.ERROR: {
      const message =
        (typeof raw.data === 'string' ? raw.data : '') ||
        readString(payload, ['detail', 'error', 'message']) ||
        'Unknown error';
      return { type: 'error', message };
    }
    default:
      return { type: 'unknown', raw };
  }
}
