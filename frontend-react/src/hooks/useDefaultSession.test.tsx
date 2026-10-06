import { StrictMode } from 'react';
import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { useWorkspaceStore } from '../store/workspace';
import { useDefaultSession } from './useDefaultSession';
import i18n from '../i18n/config';

vi.mock('../api', () => ({ api: { createSession: vi.fn() } }));

function deferred() {
  let resolve!: (value: { id: string; title?: string; status?: string }) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<{ id: string; title?: string; status?: string }>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.clearAllMocks();
  useWorkspaceStore.setState(useWorkspaceStore.getInitialState(), true);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('useDefaultSession', () => {
  it('shares one request across StrictMode effects and multiple consumers', async () => {
    const request = deferred();
    vi.mocked(api.createSession).mockReturnValue(request.promise);
    const first = renderHook(() => useDefaultSession(), { wrapper: StrictMode });
    const second = renderHook(() => useDefaultSession(), { wrapper: StrictMode });
    const insert = vi.spyOn(useWorkspaceStore.getState(), 'createSessionLocal');
    const calls = vi.mocked(api.createSession).mock.calls.length;

    await act(async () => { request.resolve({ id: 'default', title: 'Created', status: 'idle' }); });

    expect(calls).toBe(1);
    expect(api.createSession).toHaveBeenCalledWith({ title: i18n.t('anchored.nav.default_title') });
    expect(insert).toHaveBeenCalledTimes(1);
    expect(first.result.current.sessionId).toBe('default');
    expect(second.result.current.sessionId).toBe('default');
    expect(useWorkspaceStore.getState().sessions).toEqual([
      expect.objectContaining({ id: 'default', title: 'Created', status: 'idle', messages: [], activeSkills: [], activeTools: [] }),
    ]);
    insert.mockRestore();
  });

  it('keeps the result for a surviving consumer when the initiator unmounts', async () => {
    const request = deferred();
    vi.mocked(api.createSession).mockReturnValue(request.promise);
    const first = renderHook(() => useDefaultSession());
    const second = renderHook(() => useDefaultSession());
    first.unmount();

    await act(async () => { request.resolve({ id: 'survivor' }); });

    expect(api.createSession).toHaveBeenCalledTimes(1);
    expect(second.result.current).toEqual({ sessionId: 'survivor', creationError: null });
  });

  it('reuses an in-flight request after all consumers unmount and remount', async () => {
    const request = deferred();
    vi.mocked(api.createSession).mockReturnValue(request.promise);
    const first = renderHook(() => useDefaultSession());
    first.unmount();
    const next = renderHook(() => useDefaultSession());

    await act(async () => { request.resolve({ id: 'remounted' }); });

    expect(api.createSession).toHaveBeenCalledTimes(1);
    expect(next.result.current.sessionId).toBe('remounted');
  });

  it('retains a completed result even while all consumers are unmounted', async () => {
    const request = deferred();
    vi.mocked(api.createSession).mockReturnValue(request.promise);
    renderHook(() => useDefaultSession()).unmount();

    await act(async () => { request.resolve({ id: 'retained' }); });
    const next = renderHook(() => useDefaultSession());

    expect(api.createSession).toHaveBeenCalledTimes(1);
    expect(next.result.current.sessionId).toBe('retained');
  });

  it('reports failure to consumers and permits a later shared retry', async () => {
    const failed = deferred();
    vi.mocked(api.createSession).mockReturnValue(failed.promise);
    const first = renderHook(() => useDefaultSession(), { wrapper: StrictMode });
    const second = renderHook(() => useDefaultSession());

    await act(async () => { failed.reject(new Error('Creation failed')); });

    expect(first.result.current.creationError).toBe('Creation failed');
    expect(second.result.current.creationError).toBe('Creation failed');
    first.unmount();
    second.unmount();
    const retry = deferred();
    vi.mocked(api.createSession).mockReturnValue(retry.promise);
    const next = renderHook(() => useDefaultSession(), { wrapper: StrictMode });
    const peer = renderHook(() => useDefaultSession());

    await act(async () => { retry.resolve({ id: 'retried' }); });

    expect(api.createSession).toHaveBeenCalledTimes(2);
    expect(next.result.current).toEqual({ sessionId: 'retried', creationError: null });
    expect(peer.result.current.sessionId).toBe('retried');
  });

  it('preserves a manual selection made while creation is pending', async () => {
    const request = deferred();
    vi.mocked(api.createSession).mockReturnValue(request.promise);
    const consumer = renderHook(() => useDefaultSession());
    await act(async () => {
      useWorkspaceStore.getState().setActiveSession('manual');
      request.resolve({ id: 'default' });
      await request.promise;
    });

    expect(consumer.result.current.sessionId).toBe('manual');
    expect(useWorkspaceStore.getState().sessions).toEqual([]);
  });

  it('preserves sessions loaded while creation is pending', async () => {
    const request = deferred();
    vi.mocked(api.createSession).mockReturnValue(request.promise);
    const consumer = renderHook(() => useDefaultSession());
    await act(async () => {
      useWorkspaceStore.getState().loadSessions([{ id: 'loaded', title: 'Existing', status: 'idle' }]);
      request.resolve({ id: 'default' });
      await request.promise;
    });

    expect(consumer.result.current.sessionId).toBe('loaded');
    expect(useWorkspaceStore.getState().activeSessionId).toBeNull();
    expect(useWorkspaceStore.getState().sessions.map(session => session.id)).toEqual(['loaded']);
  });

  it('uses an existing session without requesting creation', () => {
    useWorkspaceStore.getState().loadSessions([{ id: 'existing', status: 'idle' }]);
    const consumer = renderHook(() => useDefaultSession(), { wrapper: StrictMode });

    expect(api.createSession).not.toHaveBeenCalled();
    expect(consumer.result.current.sessionId).toBe('existing');
  });

  it('reports a shared failure after the initiating consumer unmounts', async () => {
    const request = deferred();
    vi.mocked(api.createSession).mockReturnValue(request.promise);
    const first = renderHook(() => useDefaultSession());
    const second = renderHook(() => useDefaultSession());
    first.unmount();

    await act(async () => { request.reject('Failed'); });

    expect(api.createSession).toHaveBeenCalledTimes(1);
    expect(second.result.current).toEqual({ sessionId: null, creationError: i18n.t('anchored.nav.create_default_failed') });
  });

  it('clears an old error when the same consumer starts a later attempt', async () => {
    const failed = deferred();
    vi.mocked(api.createSession).mockReturnValue(failed.promise);
    const consumer = renderHook(() => useDefaultSession());
    await act(async () => { failed.reject(new Error('Creation failed')); });
    expect(consumer.result.current.creationError).toBe('Creation failed');

    act(() => { useWorkspaceStore.getState().setActiveSession('manual'); });
    const retry = deferred();
    vi.mocked(api.createSession).mockReturnValue(retry.promise);
    act(() => { useWorkspaceStore.getState().setActiveSession(null); });
    expect(consumer.result.current.creationError).toBeNull();
    await act(async () => { retry.resolve({ id: 'retry' }); });

    expect(api.createSession).toHaveBeenCalledTimes(2);
    expect(consumer.result.current).toEqual({ sessionId: 'retry', creationError: null });
  });
});
