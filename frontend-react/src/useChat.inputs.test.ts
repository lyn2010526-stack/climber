import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from './api';
import i18n from './i18n/config';
import { useChat } from './useChat';
import { normalizeChatEvent, type ChatStreamEvent, type SessionInput } from './types/chatEvents';

vi.mock('./api', () => ({ api: {
  getSessionMessages: vi.fn(), getSessionInputs: vi.fn(), submitSessionInput: vi.fn(), chatStream: vi.fn(), startSessionInputs: vi.fn(), getSessionInputReport: vi.fn(), resumeSessionInputs: vi.fn(),
} }));
let emit: (event: ChatStreamEvent) => void;
const item: SessionInput = { id: 'input-1', client_request_id: 'request-1', kind: 'follow_up', message: 'next', status: 'queued', sequence: 1 };
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getSessionMessages).mockResolvedValue([]);
  vi.mocked(api.getSessionInputs).mockResolvedValue([]);
  vi.mocked(api.chatStream).mockImplementation((_id, _message, callback) => { emit = callback; return vi.fn(); });
  vi.mocked(api.startSessionInputs).mockImplementation((_id, callback) => { emit = callback; return vi.fn(); });
});
afterEach(() => vi.useRealTimers());
async function start() {
  const hook = renderHook(({ id }) => useChat(id), { initialProps: { id: 'a' } });
  await act(async () => {});
  await act(async () => { await hook.result.current.sendMessage('first'); });
  return hook;
}

it('explicitly starts an idle follow-up once and waits for its turn before adding history', async () => {
  vi.mocked(api.getSessionInputs).mockResolvedValue([item]);
  const { result } = renderHook(() => useChat('a'));
  await act(async () => {});
  act(() => { result.current.startInputs(); result.current.startInputs(); });
  expect(api.startSessionInputs).toHaveBeenCalledTimes(1);
  expect(api.chatStream).not.toHaveBeenCalled();
  expect(result.current.messages).toEqual([]);
  expect(result.current.isStreaming).toBe(true);
  await act(async () => {
    emit({ type: 'turn_started', inputId: item.id, message: item.message });
    emit({ type: 'text', delta: 'answer' });
    emit({ type: 'turn_done', messageId: 'saved' });
    emit({ type: 'done' });
  });
  expect(result.current.messages.map(message => [message.role, message.content])).toEqual([['user', 'next'], ['assistant', 'answer']]);
  expect(result.current.isStreaming).toBe(false);
});

it('keeps rejected queue starts out of history and retries the queue route', async () => {
  vi.mocked(api.getSessionInputs).mockResolvedValue([item]);
  const { result } = renderHook(() => useChat('a'));
  await act(async () => {});
  act(() => result.current.startInputs());
  act(() => emit({ type: 'error', message: 'Queue is frozen' }));
  expect(result.current.messages).toEqual([]);
  expect(result.current.error).toBe('Queue is frozen');
  act(() => result.current.retry());
  expect(api.startSessionInputs).toHaveBeenCalledTimes(2);
  expect(api.chatStream).not.toHaveBeenCalled();
});

it('requires a queued follow-up and a separate explicit start after reviewed recovery', async () => {
  vi.mocked(api.getSessionInputs).mockResolvedValue([{ ...item, status: 'blocked' }]);
  vi.mocked(api.resumeSessionInputs).mockResolvedValue([item]);
  const { result } = renderHook(() => useChat('a'));
  await act(async () => {});
  act(() => result.current.startInputs());
  expect(api.startSessionInputs).not.toHaveBeenCalled();
  await act(async () => { await result.current.resumeInputs(true); });
  expect(api.startSessionInputs).not.toHaveBeenCalled();
  act(() => result.current.startInputs());
  expect(api.startSessionInputs).toHaveBeenCalledTimes(1);
});

it('preserves generic file payloads when retrying an attachment-only message', async () => {
  const files = [{ kind: 'file' as const, data: 'data:text/plain;base64,YQ==', name: 'note.txt', mime_type: 'text/plain', size: 1 }];
  const { result } = renderHook(() => useChat('a'));
  await act(async () => { await result.current.sendMessage('', undefined, files); });
  act(() => emit({ type: 'error', message: 'offline' }));
  act(() => result.current.retry());
  expect(api.chatStream).toHaveBeenLastCalledWith('a', '', expect.any(Function), { attachments: undefined, files });
  expect(result.current.messages[0].files).toEqual(files);
});

it('ignores stale queue events after a session switch and excludes steering-only queues', async () => {
  vi.mocked(api.getSessionInputs).mockResolvedValueOnce([item]).mockResolvedValue([{ ...item, kind: 'steering' }]);
  const hook = renderHook(({ id }) => useChat(id), { initialProps: { id: 'a' } });
  await act(async () => {});
  act(() => hook.result.current.startInputs());
  const staleEmit = emit;
  await act(async () => hook.rerender({ id: 'b' }));
  act(() => {
    staleEmit({ type: 'turn_started', inputId: item.id, message: item.message });
    staleEmit({ type: 'text', delta: 'stale' });
    hook.result.current.startInputs();
  });
  expect(hook.result.current.messages).toEqual([]);
  expect(hook.result.current.isStreaming).toBe(false);
  expect(api.startSessionInputs).toHaveBeenCalledTimes(1);
});

it('restores the server report on session entry and protects newer SSE from late GET', async () => {
  const report = { completed: ['saved'], executing: [], queued: ['next'], risks: [] };
  vi.mocked(api.getSessionInputReport).mockResolvedValueOnce(report);
  const hook = renderHook(() => useChat('a'));
  await act(async () => {});
  expect(hook.result.current.runtimeReport).toEqual(report);
  const late = deferred<typeof report>();
  vi.mocked(api.getSessionInputReport).mockReturnValueOnce(late.promise);
  await act(async () => { await hook.result.current.sendMessage('first'); });
  const live = { ...report, executing: ['live'] };
  act(() => emit({ type: 'runtime_report', report: live }));
  await act(async () => { late.resolve(report); });
  expect(hook.result.current.runtimeReport).toEqual(live);
});

it('recovers the report after completion and ignores a snapshot from a previous session', async () => {
  const hook = await start();
  const report = { completed: ['saved'], executing: [], queued: [], risks: [] };
  vi.mocked(api.getSessionInputReport).mockResolvedValueOnce(report);
  await act(async () => emit({ type: 'done' }));
  expect(hook.result.current.runtimeReport).toEqual(report);
  const late = deferred<typeof report>();
  vi.mocked(api.getSessionInputReport).mockReturnValueOnce(late.promise);
  hook.rerender({ id: 'b' });
  hook.rerender({ id: 'c' });
  await act(async () => late.resolve(report));
  expect(hook.result.current.runtimeReport).toBeNull();
});

it('resumes only reviewed inputs, preserves unknown effects and never starts an idle executor', async () => {
  const blocked = { ...item, status: 'blocked' as const, error: 'unknown effect' };
  vi.mocked(api.getSessionInputs).mockResolvedValueOnce([blocked]);
  const hook = renderHook(() => useChat('a'));
  await act(async () => {});
  await act(async () => { expect(await hook.result.current.resumeInputs(false)).toBe(false); });
  expect(api.resumeSessionInputs).not.toHaveBeenCalled();
  vi.mocked(api.resumeSessionInputs).mockResolvedValueOnce([blocked]);
  const report = { completed: [], executing: [], queued: [], risks: ['unknown effect'] };
  vi.mocked(api.getSessionInputReport).mockResolvedValueOnce(report);
  await act(async () => { expect(await hook.result.current.resumeInputs(true)).toBe(true); });
  expect(hook.result.current.inputs).toEqual([blocked]);
  expect(hook.result.current.runtimeReport).toEqual(report);
  expect(hook.result.current.resumeFeedback).toContain(i18n.t('anchored.resume.confirmed'));
  expect(hook.result.current.isStreaming).toBe(false);
  expect(api.chatStream).not.toHaveBeenCalled();
});

it('isolates late resume responses and prevents duplicate resume requests', async () => {
  const hook = renderHook(({ id }) => useChat(id), { initialProps: { id: 'a' } });
  await act(async () => {});
  const late = deferred<SessionInput[]>();
  vi.mocked(api.resumeSessionInputs).mockReturnValueOnce(late.promise);
  let pending!: Promise<boolean>;
  act(() => { pending = hook.result.current.resumeInputs(true); });
  expect(hook.result.current.resumePending).toBe(true);
  await act(async () => { expect(await hook.result.current.resumeInputs(true)).toBe(false); });
  expect(api.resumeSessionInputs).toHaveBeenCalledTimes(1);
  hook.rerender({ id: 'b' });
  await act(async () => { late.resolve([item]); expect(await pending).toBe(false); });
  expect(hook.result.current.inputs).toEqual([]);
  expect(hook.result.current.resumeFeedback).toBeNull();
  expect(hook.result.current.resumePending).toBe(false);
});

it('retains blocked inputs and exposes failure when resume confirmation fails', async () => {
  const blocked = { ...item, status: 'blocked' as const };
  vi.mocked(api.getSessionInputs).mockResolvedValueOnce([blocked]);
  vi.mocked(api.resumeSessionInputs).mockRejectedValueOnce(new Error('offline'));
  const hook = renderHook(() => useChat('a'));
  await act(async () => {});
  await act(async () => { expect(await hook.result.current.resumeInputs(true)).toBe(false); });
  expect(hook.result.current.inputs).toEqual([blocked]);
  expect(hook.result.current.resumeFeedback).toContain('offline');
  expect(hook.result.current.resumePending).toBe(false);
});

it('applies acknowledged safe queue recovery while retaining blocked unknown-effect items', async () => {
  const blocked = { ...item, status: 'blocked' as const };
  const unknown = { ...blocked, id: 'unknown', client_request_id: 'unknown', sequence: 2, error: 'unknown effect' };
  vi.mocked(api.getSessionInputs).mockResolvedValueOnce([blocked, unknown]);
  vi.mocked(api.resumeSessionInputs).mockResolvedValueOnce([item, unknown]);
  const hook = renderHook(() => useChat('a'));
  await act(async () => {});
  await act(async () => { await hook.result.current.resumeInputs(true); });
  expect(hook.result.current.inputs).toEqual([item, unknown]);
  expect(hook.result.current.isStreaming).toBe(false);
});

it('preserves live input progress ahead of a late resume acknowledgement', async () => {
  const hook = await start();
  const late = deferred<SessionInput[]>();
  vi.mocked(api.resumeSessionInputs).mockReturnValueOnce(late.promise);
  let pending!: Promise<boolean>;
  act(() => { pending = hook.result.current.resumeInputs(true); });
  act(() => emit({ type: 'input_status', item: { ...item, status: 'started' } }));
  await act(async () => { late.resolve([item]); await pending; });
  expect(hook.result.current.inputs[0].status).toBe('started');
});

it('ignores a late resume acknowledgement after stopping', async () => {
  const hook = await start();
  const late = deferred<SessionInput[]>();
  vi.mocked(api.resumeSessionInputs).mockReturnValueOnce(late.promise);
  let pending!: Promise<boolean>;
  act(() => { pending = hook.result.current.resumeInputs(true); });
  act(() => hook.result.current.stopStreaming());
  await act(async () => { late.resolve([item]); expect(await pending).toBe(false); });
  expect(hook.result.current.inputs).toEqual([]);
  expect(hook.result.current.resumeFeedback).toBeNull();
  expect(hook.result.current.resumePending).toBe(false);
});

it('normalizes input status and turn boundaries, rejecting malformed items', () => {
  expect(normalizeChatEvent({ event: 'input_status', data: { item } })).toEqual({ type: 'input_status', item });
  expect(normalizeChatEvent({ event: 'turn_started', data: { input_id: 'input-1', message: 'next' } })).toEqual({ type: 'turn_started', inputId: 'input-1', message: 'next' });
  expect(normalizeChatEvent({ event: 'turn_done', data: { message_id: 'server-message' } })).toEqual({ type: 'turn_done', messageId: 'server-message' });
  expect(normalizeChatEvent({ event: 'input_status', data: { item: { ...item, status: 'invented' } } }).type).toBe('unknown');
});

it('keeps pending until confirmation, retains failed input and retries the same request id', async () => {
  const { result } = await start();
  const request = deferred<SessionInput>();
  vi.mocked(api.submitSessionInput).mockReturnValueOnce(request.promise).mockResolvedValueOnce(item);
  let submission!: Promise<boolean>;
  act(() => { submission = result.current.submitInput('next', 'follow_up', 'request-1'); });
  expect(result.current.inputs[0].status).toBe('pending');
  await act(async () => { request.reject(new Error('offline')); await submission; });
  expect(result.current.inputs[0]).toMatchObject({ status: 'unconfirmed', message: 'next', error: 'offline' });
  await act(async () => { expect(await result.current.retryInput(result.current.inputs[0])).toBe(true); });
  expect(result.current.inputs).toEqual([item]);
  expect(api.submitSessionInput).toHaveBeenNthCalledWith(2, 'a', { client_request_id: 'request-1', kind: 'follow_up', message: 'next' });
});

it('preserves SSE progress ahead of a late POST response or snapshot', async () => {
  const { result } = await start();
  const post = deferred<SessionInput>();
  vi.mocked(api.submitSessionInput).mockReturnValueOnce(post.promise);
  let submission!: Promise<boolean>;
  act(() => { submission = result.current.submitInput('next', 'follow_up', 'request-1'); });
  act(() => emit({ type: 'input_status', item: { ...item, status: 'started' } }));
  await act(async () => { post.resolve(item); await submission; });
  expect(result.current.inputs[0].status).toBe('started');
});

it('isolates late streams and input confirmations after switching away and back', async () => {
  const { result, rerender } = await start();
  const oldEmit = emit;
  const post = deferred<SessionInput>();
  vi.mocked(api.submitSessionInput).mockReturnValueOnce(post.promise);
  let submission!: Promise<boolean>;
  act(() => { submission = result.current.submitInput('next', 'follow_up', 'request-1'); });
  rerender({ id: 'b' });
  rerender({ id: 'a' });
  await act(async () => { post.resolve(item); await submission; oldEmit({ type: 'text', delta: 'stale' }); oldEmit({ type: 'input_status', item }); });
  expect(result.current.messages).toEqual([]);
  expect(result.current.inputs).toEqual([]);
  expect(result.current.isStreaming).toBe(false);
});

it('creates a new assistant for each turn and scopes reused tool ids to the right turn', async () => {
  const { result } = await start();
  act(() => {
    emit({ type: 'text', delta: 'first answer' });
    emit({ type: 'tool_call', toolCall: { id: 'tool', name: 'first-tool', arguments: {} } });
    emit({ type: 'tool_result', toolCallId: 'tool', result: 'first-result', error: '' });
    emit({ type: 'turn_done', messageId: 'first-assistant' });
    emit({ type: 'turn_started', inputId: 'input-1', message: 'next' });
    emit({ type: 'turn_started', inputId: 'input-1', message: 'next' });
    emit({ type: 'text', delta: 'next answer' });
    emit({ type: 'tool_call', toolCall: { id: 'tool', name: 'next-tool', arguments: {} } });
    emit({ type: 'tool_result', toolCallId: 'tool', result: 'next-result', error: '' });
    emit({ type: 'turn_done', messageId: 'next-assistant' });
  });
  expect(result.current.isStreaming).toBe(true);
  const assistants = result.current.messages.filter(message => message.role === 'assistant');
  expect(assistants).toHaveLength(2);
  expect(assistants[0]).toMatchObject({ id: 'first-assistant', content: 'first answer', toolCalls: [{ name: 'first-tool', result: 'first-result' }] });
  expect(assistants[1]).toMatchObject({ id: 'next-assistant', content: 'next answer', toolCalls: [{ name: 'next-tool', result: 'next-result' }] });
  expect(assistants[0].toolCalls![0].id).not.toBe(assistants[1].toolCalls![0].id);
  act(() => emit({ type: 'done' }));
  expect(result.current.isStreaming).toBe(false);
});

it('polls snapshots while streaming and stops polling after done', async () => {
  vi.useFakeTimers();
  const { result } = await start();
  vi.mocked(api.getSessionInputs).mockResolvedValue([item]);
  await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
  expect(result.current.inputs).toEqual([item]);
  act(() => emit({ type: 'done' }));
  await act(async () => {});
  const count = vi.mocked(api.getSessionInputs).mock.calls.length;
  await act(async () => { await vi.advanceTimersByTimeAsync(9000); });
  expect(api.getSessionInputs).toHaveBeenCalledTimes(count);
});

it('discards a stale snapshot when SSE progresses during the request', async () => {
  vi.useFakeTimers();
  const { result } = await start();
  const snapshot = deferred<SessionInput[]>();
  vi.mocked(api.getSessionInputs).mockReturnValueOnce(snapshot.promise);
  await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
  act(() => emit({ type: 'input_status', item: { ...item, status: 'completed' } }));
  await act(async () => snapshot.resolve([item]));
  expect(result.current.inputs[0].status).toBe('completed');
});

it('ignores late callbacks after stop and keeps the next stream isolated', async () => {
  const { result } = await start();
  const oldEmit = emit;
  act(() => result.current.stopStreaming());
  await act(async () => { await result.current.sendMessage('fresh'); });
  act(() => { oldEmit({ type: 'done' }); oldEmit({ type: 'text', delta: 'stale' }); });
  expect(result.current.isStreaming).toBe(true);
  act(() => { emit({ type: 'text', delta: 'fresh answer' }); emit({ type: 'done' }); });
  expect(result.current.messages.at(-1)?.content).toBe('fresh answer');
});

it.each([undefined, 'turn-assistant'])('fills final done content after turn_done with message id %s', async messageId => {
  const { result } = await start();
  act(() => {
    emit(normalizeChatEvent({ event: 'turn_started', data: { input_id: null, message: 'first' } }));
    emit(normalizeChatEvent({ event: 'turn_done', data: { input_id: null, turn_id: 'turn-1', status: 'completed', message_id: messageId } }));
    emit(normalizeChatEvent({ event: 'done', data: { content: 'final fallback', message_id: 'persisted-assistant', status: 'completed' } }));
  });
  expect(result.current.messages).toHaveLength(2);
  expect(result.current.messages[1]).toMatchObject({ id: 'persisted-assistant', content: 'final fallback' });
  expect(result.current.isStreaming).toBe(false);
});

it('keeps streamed text and independently renames the last queued turn on final done', async () => {
  const { result } = await start();
  act(() => {
    emit({ type: 'text', delta: 'first answer' });
    emit({ type: 'turn_done', messageId: 'first-id' });
    emit({ type: 'turn_started', inputId: 'input-1', message: 'next' });
    emit({ type: 'text', delta: 'next answer' });
    emit({ type: 'turn_done', messageId: 'next-id' });
    emit({ type: 'done', messageId: 'final-id', content: 'duplicate final content' });
  });
  expect(result.current.messages.filter(message => message.role === 'assistant').map(message => [message.id, message.content])).toEqual([
    ['first-id', 'first answer'], ['final-id', 'next answer'],
  ]);
});

it('flushes a tail buffered after turn_done into its final renamed message', async () => {
  const { result } = await start();
  act(() => {
    emit({ type: 'text', delta: 'start' });
    emit({ type: 'turn_done', messageId: 'turn-id' });
    emit({ type: 'text', delta: ' tail' });
    emit({ type: 'done', messageId: 'final-id', content: 'fallback' });
  });
  expect(result.current.messages[1]).toMatchObject({ id: 'final-id', content: 'start tail' });
});

it('marks an error received after turn_done on the last assistant', async () => {
  const { result } = await start();
  act(() => { emit({ type: 'turn_done' }); emit({ type: 'error', message: 'queue interrupted' }); });
  expect(result.current.messages[1].failed).toBe(true);
});

it('normalizes genuine runtime report values and distinguishes missing fields from empty arrays', () => {
  expect(normalizeChatEvent({ event: 'runtime_report', data: { completed: ['saved'], executing: 'checking', queued: [], risks: 0 } })).toEqual({
    type: 'runtime_report', report: { completed: ['saved'], executing: ['checking'], queued: [], risks: null },
  });
  expect(normalizeChatEvent({ event: '', data: { type: 'runtime_report', risks: ['review required'] } })).toEqual({
    type: 'runtime_report', report: { completed: null, executing: null, queued: null, risks: ['review required'] },
  });
});

it('keeps reports through done, clears them on new runs and isolates late session reports', async () => {
  const { result, rerender } = await start();
  const report = { completed: ['saved'], executing: [], queued: [], risks: ['review required'] };
  act(() => { emit({ type: 'runtime_report', report }); emit({ type: 'done' }); });
  expect(result.current.runtimeReport).toEqual(report);
  await act(async () => { await result.current.sendMessage('fresh'); });
  expect(result.current.runtimeReport).toBeNull();
  act(() => emit({ type: 'runtime_report', report }));
  const oldEmit = emit;
  rerender({ id: 'b' });
  act(() => oldEmit({ type: 'runtime_report', report }));
  expect(result.current.runtimeReport).toBeNull();
});
