import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useChatStore } from '../chat';

vi.mock('../../lib/api-client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    stream: vi.fn(),
  },
}));

import { apiClient } from '../../lib/api-client';

describe('ChatStore', () => {
  beforeEach(() => {
    useChatStore.setState({
      sessions: [],
      messages: [],
      isStreaming: false,
      error: null,
      activeSessionId: null,
      abortFn: null,
    });
    vi.clearAllMocks();
  });

  it('initial state is correct', () => {
    const state = useChatStore.getState();
    expect(state.messages).toEqual([]);
    expect(state.isStreaming).toBe(false);
    expect(state.error).toBeNull();
    expect(state.activeSessionId).toBeNull();
  });

  it('setActiveSession sets session and clears messages', async () => {
    (apiClient.get as any).mockResolvedValue([]);
    useChatStore.getState().setActiveSession('session-1');
    const state = useChatStore.getState();
    expect(state.activeSessionId).toBe('session-1');
    expect(state.messages).toEqual([]);
    expect(state.error).toBeNull();
  });

  it('setActiveSession with null clears messages', () => {
    useChatStore.setState({ messages: [{ id: '1', role: 'user', content: 'created_at', tool_calls: [], created_at: '2024-01-01' }] });
    useChatStore.getState().setActiveSession(null);
    expect(useChatStore.getState().messages).toEqual([]);
  });

  it('clearMessages resets messages and error', () => {
    useChatStore.setState({
      messages: [{ id: '1', role: 'user', content: 'test', tool_calls: [], created_at: '2024-01-01' }],
      error: 'some error',
    });
    useChatStore.getState().clearMessages();
    expect(useChatStore.getState().messages).toEqual([]);
    expect(useChatStore.getState().error).toBeNull();
  });

  it('stopStreaming calls abortFn and resets state', () => {
    const mockAbort = vi.fn();
    useChatStore.setState({ isStreaming: true, abortFn: mockAbort });
    useChatStore.getState().stopStreaming();
    expect(mockAbort).toHaveBeenCalled();
    expect(useChatStore.getState().isStreaming).toBe(false);
    expect(useChatStore.getState().abortFn).toBeNull();
  });

  it('sendMessage does nothing if isStreaming', async () => {
    useChatStore.setState({ isStreaming: true, activeSessionId: 'session-1' });
    await useChatStore.getState().sendMessage('hello');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('sendMessage does nothing if content is empty', async () => {
    useChatStore.setState({ activeSessionId: 'session-1' });
    await useChatStore.getState().sendMessage('');
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('sendMessage adds user and assistant messages', async () => {
    useChatStore.setState({ activeSessionId: 'session-1' });
    await useChatStore.getState().sendMessage('hello');
    const state = useChatStore.getState();
    expect(state.messages.length).toBe(2);
    expect(state.messages[0].role).toBe('user');
    expect(state.messages[0].content).toBe('hello');
    expect(state.messages[1].role).toBe('assistant');
    expect(state.isStreaming).toBe(true);
  });

  it('setActiveSession fetches messages on success', async () => {
    (apiClient.get as any).mockResolvedValue([
      { id: 'm1', role: 'user', content: 'hi', created_at: '2024-01-01T00:00:00Z' },
    ]);
    useChatStore.getState().setActiveSession('session-1');
    await new Promise((r) => setTimeout(r, 100));
    const state = useChatStore.getState();
    expect(state.messages.length).toBe(1);
    expect(state.messages[0].id).toBe('m1');
  });

  it('setActiveSession handles fetch error', async () => {
    (apiClient.get as any).mockRejectedValue(new Error('fail'));
    useChatStore.getState().setActiveSession('session-1');
    await new Promise((r) => setTimeout(r, 100));
    expect(useChatStore.getState().messages).toEqual([]);
  });

  it('sendMessage creates session when activeSessionId is null', async () => {
    (apiClient.post as any).mockResolvedValue({ id: 'new-session', title: 'New Chat' });
    await useChatStore.getState().sendMessage('hello');
    const state = useChatStore.getState();
    expect(state.activeSessionId).toBe('new-session');
    expect(state.messages.length).toBe(2);
  });
});
