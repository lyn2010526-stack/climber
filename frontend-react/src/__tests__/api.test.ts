import { afterEach, describe, expect, it, vi } from 'vitest';

import { api } from '../api';

describe('ApiClient paginated lists', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('returns agent items from the paginated response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ id: 'agent-1', name: 'Planner' }],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    }));

    await expect(api.listAgents()).resolves.toEqual([
      { id: 'agent-1', name: 'Planner' },
    ]);
  });

  it('returns session items from the paginated response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ id: 'session-1', title: 'Investigation', status: 'idle' }],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    }));

    await expect(api.listSessions()).resolves.toEqual([
      { id: 'session-1', title: 'Investigation', status: 'idle' },
    ]);
  });

  it('sends the stored bearer token with API requests', async () => {
    localStorage.setItem('auth_token', 'signed-token');
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
    localStorage.setItem('auth_token', 'signed-token');
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
});
