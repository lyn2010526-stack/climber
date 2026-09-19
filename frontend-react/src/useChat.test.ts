import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api, type SessionMessage } from './api';
import { useChat } from './useChat';

vi.mock('./api', () => ({ api: { getSessionMessages: vi.fn() } }));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function history(id: string): SessionMessage[] {
  return [{
    id, role: 'assistant', content: id, tool_calls: [],
    tool_call_id: null, tool_name: null, created_at: '2026-01-01T00:00:00Z',
  }];
}

beforeEach(() => vi.resetAllMocks());

describe('useChat history lifecycle', () => {
  it('clears old messages immediately while the next session loads', async () => {
    vi.mocked(api.getSessionMessages)
      .mockResolvedValueOnce(history('a'))
      .mockReturnValueOnce(deferred<SessionMessage[]>().promise);
    const { result, rerender } = renderHook(({ id }) => useChat(id), {
      initialProps: { id: 'a' as string | null },
    });
    await act(async () => {});
    expect(result.current.messages[0].id).toBe('a');
    rerender({ id: 'b' });
    expect(result.current.messages).toEqual([]);
    rerender({ id: null });
    expect(result.current.messages).toEqual([]);
    expect(api.getSessionMessages).toHaveBeenCalledTimes(2);
  });

  it.each(['success', 'failure'])('ignores late %s after switching sessions', async (outcome) => {
    const old = deferred<SessionMessage[]>();
    vi.mocked(api.getSessionMessages)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce(history('b'));
    const { result, rerender } = renderHook(({ id }) => useChat(id), {
      initialProps: { id: 'a' },
    });
    rerender({ id: 'b' });
    await act(async () => {});
    expect(result.current.messages[0].id).toBe('b');
    await act(async () => {
      if (outcome === 'success') old.resolve(history('a'));
      else old.reject(new Error('History failed'));
    });
    expect(result.current.messages.map(message => message.id)).toEqual(['b']);
  });

  it.each(['success', 'failure'])('ignores late %s after clearing the session', async (outcome) => {
    const old = deferred<SessionMessage[]>();
    vi.mocked(api.getSessionMessages).mockReturnValueOnce(old.promise);
    const { result, rerender } = renderHook(({ id }) => useChat(id), {
      initialProps: { id: 'a' as string | null },
    });
    rerender({ id: null });
    await act(async () => {
      if (outcome === 'success') old.resolve(history('a'));
      else old.reject(new Error('History failed'));
    });
    expect(result.current.messages).toEqual([]);
    expect(api.getSessionMessages).toHaveBeenCalledTimes(1);
  });

  it('discards history before processing it after unmount', async () => {
    const old = deferred<SessionMessage[]>();
    vi.mocked(api.getSessionMessages).mockReturnValueOnce(old.promise);
    const { unmount } = renderHook(() => useChat('a'));
    unmount();
    const messages = history('a');
    const map = vi.spyOn(messages, 'map');
    await act(async () => old.resolve(messages));
    expect(map).not.toHaveBeenCalled();
  });

  it('handles a rejected history request after unmount', async () => {
    const old = deferred<SessionMessage[]>();
    vi.mocked(api.getSessionMessages).mockReturnValueOnce(old.promise);
    const { unmount } = renderHook(() => useChat('a'));
    unmount();
    await act(async () => old.reject(new Error('History failed')));
  });
});
