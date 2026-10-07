import type { GroupTaskNode, TaskSummary } from '../../api';
import { api } from '../../api';

export type { GroupSnapshot, GroupTaskNode } from '../../api';

export interface LiveTask extends TaskSummary {
  error?: string | null;
  interruption_reason?: string | null;
  retry_count?: number;
}

export interface TaskEvent {
  type: string;
  task_id: string;
  protocol_version: number;
  epoch: string;
  sequence: number;
  data: Partial<LiveTask> & { type?: string; step?: number; total?: number };
}

export const isTerminalTask = (status: string) => ['completed', 'failed', 'cancelled'].includes(status);
const TASK_STATUSES = new Set(['pending', 'running', 'paused', 'retrying', 'completed', 'failed', 'cancelled']);

export class TaskStreamError extends Error {
  constructor(message: string, public readonly retryable = true, public readonly retryAfterMs = 0) {
    super(message);
  }
}

export function mergeTaskEvent(task: LiveTask, event: TaskEvent, cursor?: { epoch: string; sequence: number }): LiveTask {
  if (event.task_id !== task.task_id || event.protocol_version !== 1) return task;
  if (cursor?.epoch === event.epoch && event.sequence <= cursor.sequence) return task;
  if (cursor && cursor.epoch !== event.epoch && event.type !== 'snapshot') return task;
  const eventStatus = typeof event.data.status === 'string' && TASK_STATUSES.has(event.data.status)
    ? event.data.status
    : event.data.type === 'task_retry' ? 'retrying' : task.status;
  return { ...task, ...(event.type === 'snapshot' ? { error: null, interruption_reason: null, retry_count: 0 } : {}), ...event.data, task_id: task.task_id,
    progress: event.data.progress ?? event.data.step ?? task.progress,
    total_steps: event.data.total_steps ?? event.data.total ?? task.total_steps,
    status: eventStatus };
}

export async function consumeTaskEvents(taskId: string, signal: AbortSignal, onEvent: (event: TaskEvent) => void): Promise<void> {
  if (signal.aborted) return;
  const controller = new AbortController();
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  const decoder = new TextDecoder();
  let buffer = '';
  let idleTimer: ReturnType<typeof setTimeout>;
  let timedOut = false;
  const cancel = () => { controller.abort(); void reader?.cancel().catch(() => undefined); };
  const armTimer = () => {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { timedOut = true; cancel(); }, 45000);
  };
  const dispatch = (block: string) => {
    const data = block.split(/\r?\n/).filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).trimStart()).join('\n');
    if (!data) return;
    let event: TaskEvent;
    try { event = JSON.parse(data) as TaskEvent; } catch { throw new TaskStreamError('任务事件格式无效', false); }
    if (!event || typeof event.type !== 'string' || event.task_id !== taskId || event.protocol_version !== 1 || typeof event.epoch !== 'string'
      || !Number.isSafeInteger(event.sequence) || event.sequence < 0 || !event.data || typeof event.data !== 'object' || Array.isArray(event.data)) {
      throw new TaskStreamError('任务事件格式无效', false);
    }
    onEvent(event);
  };
  signal.addEventListener('abort', cancel, { once: true });
  try {
    if (signal.aborted) return;
    armTimer();
    const response = await api.streamTaskEvents(taskId, controller.signal);
    if (signal.aborted) { await response.body?.cancel(); return; }
    if (!response.ok) {
      await response.body?.cancel();
      const retryAfter = response.headers.get('Retry-After');
      const seconds = retryAfter === null ? NaN : Number(retryAfter);
      const delay = Number.isFinite(seconds) ? seconds * 1000 : Date.parse(retryAfter ?? '') - Date.now();
      throw new TaskStreamError(`任务事件连接失败：HTTP ${response.status}`,
        response.status === 429 || response.status >= 500, Number.isFinite(delay) ? Math.max(0, delay) : 0);
    }
    if (!response.body) throw new TaskStreamError('任务事件响应缺少数据流', false);
    reader = response.body.getReader();
    while (!signal.aborted) {
      const { done, value } = await reader.read();
      if (done) break;
      armTimer();
      buffer += decoder.decode(value, { stream: true });
      if (buffer.length > 1_048_576) throw new TaskStreamError('任务事件帧超过大小限制', false);
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? '';
      for (const block of blocks) { if (signal.aborted) break; dispatch(block); }
    }
    if (timedOut) throw new Error('任务事件连接超时');
    if (!signal.aborted) dispatch(buffer + decoder.decode());
  } catch (cause) {
    if (signal.aborted) return;
    if (timedOut) throw new TaskStreamError('任务事件连接超时');
    throw cause;
  } finally {
    clearTimeout(idleTimer!);
    signal.removeEventListener('abort', cancel);
    controller.abort();
    await reader?.cancel().catch(() => undefined);
    reader?.releaseLock();
  }
}

export const listTaskGroups = (signal: AbortSignal) => api.listGroupsSimple(signal);
export const getGroupTaskSnapshot = (groupId: string, signal: AbortSignal) =>
  api.getGroupSnapshot(groupId, signal);

export function buildGroupTaskForest(nodes: GroupTaskNode[]): Array<GroupTaskNode & { children: ReturnType<typeof buildGroupTaskForest> }> {
  const indexed = new Map(nodes.map(node => [node.node_id, { ...node, children: [] as ReturnType<typeof buildGroupTaskForest> }]));
  const roots: ReturnType<typeof buildGroupTaskForest> = [];
  for (const node of indexed.values()) {
    const ancestors = new Set([node.node_id]);
    let parent = indexed.get(node.parent_id ?? '');
    let ancestor = parent;
    while (ancestor && !ancestors.has(ancestor.node_id)) {
      ancestors.add(ancestor.node_id);
      ancestor = indexed.get(ancestor.parent_id ?? '');
    }
    if (ancestor) parent = undefined;
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  return roots;
}
