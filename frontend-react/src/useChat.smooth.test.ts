import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, type ChatStreamEvent } from './api';
import { useChat } from './useChat';

vi.mock('./api', () => ({ api: { getSessionMessages: vi.fn(), chatStream: vi.fn() } }));

type ChatEventHandler = (event: ChatStreamEvent) => void;

let emit: ChatEventHandler | undefined;
const abort = vi.fn();

/** 手动驱动的 rAF 队列：测试自己决定哪一帧到来，cancel 真正出队。 */
let frames: FrameRequestCallback[];
const frameIds = new Map<number, FrameRequestCallback>();

/**
 * 可控墙钟：useChat 现在按 FLUSH_MIN_INTERVAL_MS 对「落地」做时间门控（任务48
 * 要求渲染与分片到达解耦）。测试同步驱动帧、真实 performance.now() 几乎不前进，
 * 会卡在门控上。这里 stub performance.now，并在每帧前进足够大的步长，让门控
 * 对每一帧放行，于是「每帧释放一部分、后续帧追赶到全量」的缓动断言保持成立。
 */
let now = 0;

function runFrame(): void {
  const next = frames.shift();
  now += 1000;
  if (next) act(() => { next(0); });
}

function drainFrames(maxFrames = 100): void {
  for (let i = 0; i < maxFrames && frames.length > 0; i += 1) runFrame();
}

async function startTurn(content = 'hi') {
  const { result } = renderHook(() => useChat('session-1'));
  await act(async () => {});
  await act(async () => { await result.current.sendMessage(content); });
  return { result };
}

beforeEach(() => {
  vi.resetAllMocks();
  frames = [];
  frameIds.clear();
  emit = undefined;
  abort.mockClear();
  vi.mocked(api.getSessionMessages).mockResolvedValue([]);
  vi.mocked(api.chatStream).mockImplementation((_sessionId, _message, handler) => {
    emit = handler;
    return abort;
  });
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    const id = frameIds.size + 1;
    frameIds.set(id, callback);
    frames.push(callback);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => {
    const callback = frameIds.get(id);
    if (callback) {
      frames = frames.filter(pending => pending !== callback);
      frameIds.delete(id);
    }
  });
  now = 0;
  vi.spyOn(performance, 'now').mockImplementation(() => now);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('useChat smooth streaming', () => {
  it('buffers tokens and lands them on the frame loop instead of per token', async () => {
    const { result } = await startTurn();
    act(() => {
      emit!({ type: 'text', delta: '你好' });
      emit!({ type: 'text', delta: '，世' });
      emit!({ type: 'text', delta: '界' });
    });
    // 帧未到：缓冲里的增量尚未进入画面。
    expect(result.current.messages[1].content).toBe('');
    runFrame();
    // 缓动：一帧释放一部分，剩余的随后续帧追上。
    expect(result.current.messages[1].content.length).toBeGreaterThan(0);
    expect(result.current.messages[1].content.length).toBeLessThan(5);
    drainFrames();
    expect(result.current.messages[1].content).toBe('你好，世界');
    expect(frames).toHaveLength(0);
  });

  it('eases a large backlog over multiple frames and catches up completely', async () => {
    const { result } = await startTurn();
    const backlog = 'a'.repeat(120);
    act(() => { emit!({ type: 'text', delta: backlog }); });
    runFrame();
    const afterFirstFrame = result.current.messages[1].content.length;
    expect(afterFirstFrame).toBeGreaterThan(0);
    expect(afterFirstFrame).toBeLessThan(120);
    // 每帧释放约 1/8 的积压，指数追赶到全量。
    drainFrames();
    expect(result.current.messages[1].content).toBe(backlog);
    expect(frames).toHaveLength(0);
  });

  it('buffers thinking deltas through the same frame loop', async () => {
    const { result } = await startTurn();
    act(() => {
      emit!({ type: 'thinking', delta: '先看' });
      emit!({ type: 'thinking', delta: '解析器' });
    });
    expect(result.current.messages[1].reasoning).toBeUndefined();
    drainFrames();
    expect(result.current.messages[1].reasoning).toBe('先看解析器');
    expect(frames).toHaveLength(0);
  });

  it('flushes the whole buffer when the stream completes', async () => {
    const { result } = await startTurn();
    act(() => {
      emit!({ type: 'text', delta: '最终答案' });
      emit!({ type: 'done', messageId: 'm-1' });
    });
    expect(result.current.messages[1].content).toBe('最终答案');
    expect(result.current.messages[1].id).toBe('m-1');
    expect(result.current.isStreaming).toBe(false);
    expect(frames).toHaveLength(0);
  });
});

describe('useChat stop and failure', () => {
  it('preserves failed tool results across later calls and done', async () => {
    const { result } = await startTurn();
    act(() => {
      emit!({ type: 'tool_call', toolCall: { id: 'one', name: 'read', arguments: {}, requiresApproval: true } });
      emit!({ type: 'tool_result', toolCallId: 'one', result: '', error: 'broken' });
      emit!({ type: 'tool_call', toolCall: { id: 'two', name: 'read', arguments: {} } });
      emit!({ type: 'done' });
    });
    expect(result.current.messages[1].toolCalls?.[0]).toMatchObject({ status: 'error', error: 'broken', requiresApproval: false });
    expect(result.current.messages[1].toolCalls?.[1].status).toBe('running');
  });
  it('aborts, flushes the buffer and marks the turn interrupted on stop', async () => {
    const { result } = await startTurn();
    act(() => { emit!({ type: 'text', delta: '写到一半' }); });
    await act(async () => { result.current.stopStreaming(); });
    expect(abort).toHaveBeenCalledOnce();
    expect(result.current.messages[1].content).toBe('写到一半');
    expect(result.current.messages[1].interrupted).toBe(true);
    expect(result.current.messages[1].failed).toBeUndefined();
    expect(result.current.isStreaming).toBe(false);
  });

  it('marks the turn failed and keeps partial text on a stream error', async () => {
    const { result } = await startTurn();
    act(() => {
      emit!({ type: 'text', delta: '部分输出' });
      emit!({ type: 'error', message: '上游连接失败' });
    });
    expect(result.current.error).toBe('上游连接失败');
    expect(result.current.messages[1].content).toBe('部分输出');
    expect(result.current.messages[1].failed).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(frames).toHaveLength(0);
  });

  it('does not send again while a turn is streaming', async () => {
    const { result } = await startTurn('first');
    await act(async () => { await result.current.sendMessage('second'); });
    expect(vi.mocked(api.chatStream)).toHaveBeenCalledTimes(1);
  });
});

describe('useChat retry', () => {
  it('resends the last user message as a fresh turn', async () => {
    const { result } = await startTurn('第一问');
    act(() => { emit!({ type: 'error', message: '上游连接失败' }); });
    await act(async () => { result.current.retry(); });
    expect(vi.mocked(api.chatStream)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.chatStream).mock.calls[1][1]).toBe('第一问');
  });

  it('refuses to retry while streaming and without a prior user turn', async () => {
    const { result } = await startTurn();
    await act(async () => { result.current.retry(); });
    expect(vi.mocked(api.chatStream)).toHaveBeenCalledTimes(1);

    const empty = renderHook(() => useChat('session-1'));
    await act(async () => {});
    await act(async () => { empty.result.current.retry(); });
    expect(vi.mocked(api.chatStream)).toHaveBeenCalledTimes(1);
  });
});

describe('useChat session lifecycle with in-flight streams', () => {
  it('aborts the in-flight stream when the session changes', async () => {
    const { result, rerender } = renderHook(({ id }) => useChat(id), {
      initialProps: { id: 'a' as string | null },
    });
    await act(async () => {});
    await act(async () => { await result.current.sendMessage('hi'); });
    rerender({ id: 'b' });
    expect(abort).toHaveBeenCalledOnce();
    expect(result.current.isStreaming).toBe(false);
  });

  it('drops buffered-but-unrendered text on unmount', async () => {
    const { result, unmount } = renderHook(() => useChat('session-1'));
    await act(async () => {});
    await act(async () => { await result.current.sendMessage('hi'); });
    act(() => { emit!({ type: 'text', delta: '未渲染的尾巴' }); });
    unmount();
    // 卸载后再来的帧回调不能落到任何会话的记录里。
    const before = frames.length;
    if (before > 0) drainFrames();
    expect(result.current.messages).toHaveLength(2);
  });
});
