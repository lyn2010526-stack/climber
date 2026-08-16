import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../api';

// Mock localStorage for test environment
const mockStore: Record<string, string> = {};
const mockLocalStorage = {
  getItem: vi.fn((key: string) => mockStore[key] || null),
  setItem: vi.fn((key: string, value: string) => { mockStore[key] = value; }),
  removeItem: vi.fn((key: string) => { delete mockStore[key]; }),
  clear: vi.fn(() => { Object.keys(mockStore).forEach(k => delete mockStore[k]); }),
};

beforeEach(() => {
  vi.stubGlobal('localStorage', mockLocalStorage);
});

afterEach(() => {
  vi.unstubAllGlobals();
  mockLocalStorage.clear();
  api.resetCache();
});

describe('ApiClient paginated lists', () => {
  it('returns agent items from the paginated response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ id: 'agent-1', name: 'Planner' }],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.listAgents()).resolves.toEqual([
      { id: 'agent-1', name: 'Planner' },
    ]);
  });

  it('returns session items from the paginated response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ id: 'session-1', title: 'Investigation', status: 'idle' }],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.listSessions()).resolves.toEqual([
      { id: 'session-1', title: 'Investigation', status: 'idle' },
    ]);
  });

  it('sends the stored bearer token with API requests', async () => {
    mockLocalStorage.setItem('auth_token', 'signed-token');
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], total: 0, limit: 50, offset: 0 }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await api.listAgents();

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/agents', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer signed-token' }),
    }));
  });

  it('sends the stored bearer token with chat streams', () => {
    mockLocalStorage.setItem('auth_token', 'signed-token');
    const fetchMock = vi.fn().mockReturnValue(new Promise(() => {}));
    vi.stubGlobal('fetch', fetchMock);

    const cancel = api.chatStream('session-1', 'hello', vi.fn());

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/sessions/session-1/chat',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer signed-token' }),
      }),
    );
    cancel();
  });

  it('sends the selected provider and model with chat streams', () => {
    const fetchMock = vi.fn().mockReturnValue(new Promise(() => {}));
    vi.stubGlobal('fetch', fetchMock);

    const cancel = api.chatStream('session-1', 'hello', vi.fn(), {
      provider: 'anthropic',
      modelId: 'claude-sonnet',
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/sessions/session-1/chat',
      expect.objectContaining({
        body: JSON.stringify({
          message: 'hello',
          provider: 'anthropic',
          model_id: 'claude-sonnet',
        }),
      }),
    );
    cancel();
  });
});
