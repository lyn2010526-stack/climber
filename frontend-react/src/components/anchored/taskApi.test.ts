import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildGroupTaskForest, consumeTaskEvents, mergeTaskEvent, TaskStreamError, type TaskEvent } from './taskApi';

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.removeItem('auth_token'); });
const task = { task_id: 't', objective: 'real', status: 'running', progress: 0, total_steps: 2 };
const event: TaskEvent = { type: 'task_update', task_id: 't', epoch: 'a', sequence: 2, protocol_version: 1, data: { progress: 1 } };

describe('task event contract', () => {
  it('merges partial updates and rejects duplicates, stale frames, wrong tasks and epochs', () => {
    expect(mergeTaskEvent(task, event)).toMatchObject({ objective: 'real', progress: 1 });
    expect(mergeTaskEvent(task, { ...event, data: { step: 3, total: 5 } })).toMatchObject({ progress: 3, total_steps: 5 });
    for (const invalid of [{ ...event, sequence: 1 }, { ...event, task_id: 'other' }, { ...event, epoch: 'b' }]) {
      expect(mergeTaskEvent(task, invalid, { epoch: 'a', sequence: 1 })).toBe(task);
    }
    expect(mergeTaskEvent(task, { ...event, type: 'snapshot', epoch: 'b', data: { status: 'failed' } }, { epoch: 'a', sequence: 3 })).toMatchObject({ status: 'failed' });
    expect(mergeTaskEvent(task, { ...event, data: { type: 'task_retry' } })).toMatchObject({ status: 'retrying' });
  });

  it('consumes authenticated chunked CRLF SSE, heartbeat, UTF-8 and trailing frames', async () => {
    localStorage.setItem('auth_token', 'test-token');
    const frames = `: keep-alive\r\n\r\ndata: ${JSON.stringify({ ...event, type: 'snapshot', data: { ...task, objective: '真实任务' } })}\r\n\r\ndata: ${JSON.stringify(event)}`;
    const bytes = new TextEncoder().encode(frames);
    const fetchMock = vi.fn().mockResolvedValue(new Response(new ReadableStream({ start(controller) {
      for (let offset = 0; offset < bytes.length; offset += 7) controller.enqueue(bytes.slice(offset, offset + 7));
      controller.close();
    } })));
    vi.stubGlobal('fetch', fetchMock);
    const received = vi.fn();
    await consumeTaskEvents('t', new AbortController().signal, received);
    expect(received).toHaveBeenCalledTimes(2);
    expect(received.mock.calls[0][0].data.objective).toBe('真实任务');
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/tasks/t/events', expect.objectContaining({ headers: { Authorization: 'Bearer test-token', Accept: 'text/event-stream' } }));
  });

  it('reports HTTP and invalid-frame errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response('', { status: 403 })).mockResolvedValueOnce(new Response('data: {}\n\n')));
    await expect(consumeTaskEvents('t', new AbortController().signal, vi.fn())).rejects.toThrow('HTTP 403');
    await expect(consumeTaskEvents('t', new AbortController().signal, vi.fn())).rejects.toThrow('格式无效');
  });

  it('cancels the reader on unmount and on idle timeout', async () => {
    const cancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.resolve(new Response(new ReadableStream({ cancel })))));
    const controller = new AbortController();
    const reading = consumeTaskEvents('t', controller.signal, vi.fn());
    await Promise.resolve();
    controller.abort();
    await reading;
    expect(cancel).toHaveBeenCalledTimes(1);
    vi.useFakeTimers();
    const timeout = consumeTaskEvents('t', new AbortController().signal, vi.fn());
    const rejection = expect(timeout).rejects.toThrow('超时');
    await vi.advanceTimersByTimeAsync(45000);
    await rejection;
  });

  it('preserves rate-limit metadata, releases rejected bodies and parses Retry-After dates', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-02T00:00:00Z'));
    const cancel = vi.fn();
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(new ReadableStream({ cancel }), { status: 429, headers: { 'Retry-After': '30' } }))
      .mockResolvedValueOnce(new Response('', { status: 429, headers: { 'Retry-After': 'Fri, 02 Oct 2026 00:01:00 GMT' } })));
    await expect(consumeTaskEvents('t', new AbortController().signal, vi.fn())).rejects.toMatchObject({ retryable: true, retryAfterMs: 30000 });
    expect(cancel).toHaveBeenCalledTimes(1);
    await expect(consumeTaskEvents('t', new AbortController().signal, vi.fn())).rejects.toMatchObject({ retryAfterMs: 60000 });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('times out the HTTP connection phase and aborts fetch', async () => {
    vi.useFakeTimers();
    let requestSignal!: AbortSignal;
    vi.stubGlobal('fetch', vi.fn().mockImplementation((_url, options) => new Promise((_resolve, reject) => {
      requestSignal = options.signal;
      requestSignal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    })));
    const reading = consumeTaskEvents('t', new AbortController().signal, vi.fn());
    const rejection = expect(reading).rejects.toThrow('超时');
    await vi.advanceTimersByTimeAsync(45000);
    await rejection;
    expect(requestSignal.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('does not fetch pre-aborted subscriptions or dispatch remaining buffered frames after abort', async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(new Response(`data: ${JSON.stringify(event)}\n\ndata: ${JSON.stringify(event)}\n\n`));
    vi.stubGlobal('fetch', fetchMock);
    controller.abort();
    await consumeTaskEvents('t', controller.signal, vi.fn());
    expect(fetchMock).not.toHaveBeenCalled();
    const active = new AbortController();
    const received = vi.fn(() => active.abort());
    await consumeTaskEvents('t', active.signal, received);
    expect(received).toHaveBeenCalledTimes(1);
  });

  it('reports partial-frame disconnects and releases the stream lock', async () => {
    const body = new ReadableStream<Uint8Array>({ start(controller) {
      controller.enqueue(new TextEncoder().encode('data: {"type":'));
      controller.close();
    } });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
    await expect(consumeTaskEvents('t', new AbortController().signal, vi.fn())).rejects.toBeInstanceOf(TaskStreamError);
    expect(body.locked).toBe(false);
  });

  it('propagates reader failures and clears idle timers and reader locks', async () => {
    vi.useFakeTimers();
    const body = new ReadableStream<Uint8Array>({ pull(controller) { controller.error(new Error('socket disconnected')); } });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
    await expect(consumeTaskEvents('t', new AbortController().signal, vi.fn())).rejects.toThrow('socket disconnected');
    expect(body.locked).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('clears stale errors when an authoritative snapshot reports their absence', () => {
    expect(mergeTaskEvent({ ...task, error: 'old', interruption_reason: 'paused', retry_count: 2 }, { ...event, type: 'snapshot', data: task }))
      .toMatchObject({ error: null, interruption_reason: null, retry_count: 0 });
  });
});

it('builds only reported parent links, keeps orphans and handles cycles', () => {
  const node = (node_id: string, parent_id: string | null) => ({ node_id, parent_id, task_name: node_id, status: 'running', elapsed_ms: 12 });
  const roots = buildGroupTaskForest([node('child', 'root'), node('root', null), node('orphan', 'absent'), node('a', 'b'), node('b', 'a')]);
  expect(roots.map(root => root.node_id)).toEqual(['root', 'orphan', 'a', 'b']);
  expect(roots[0].children[0].node_id).toBe('child');
  expect(roots[1].parent_id).toBe('absent');
});

it('keeps self loops, long cycles, descendants and duplicate IDs bounded and renders every unique node once', () => {
  const node = (node_id: string, parent_id: string | null) => ({ node_id, parent_id, task_name: node_id, status: 'running', elapsed_ms: 0 });
  const forest = buildGroupTaskForest([node('self', 'self'), node('a', 'b'), node('b', 'c'), node('c', 'a'), node('leaf', 'a'), node('dup', null), node('dup', 'self')]);
  const ids: string[] = [];
  const visit = (nodes: typeof forest) => { for (const entry of nodes) { ids.push(entry.node_id); visit(entry.children); } };
  visit(forest);
  expect(ids.sort()).toEqual(['a', 'b', 'c', 'dup', 'leaf', 'self']);
  expect(new Set(ids).size).toBe(ids.length);
});
