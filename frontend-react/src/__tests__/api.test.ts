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

  // Spec update (R12-H61): the cluster create endpoint requires `name`, so the
  // client must send that field rather than the former `requirements` payload.
  it('posts the required name field when creating a cluster node', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'node-1', name: 'worker-a' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await api.createCluster({ name: 'worker-a' });

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/cluster/create', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ name: 'worker-a' }),
    }));
  });

  // Spec update (R12-H62): FastAPI 422 bodies carry `detail` as an array, which
  // must be flattened into a readable message instead of "[object Object]".
  it('flattens a 422 validation detail array into the error message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [
          { loc: ['body', 'name'], msg: 'field required', type: 'value_error.missing' },
          { loc: ['body', 'endpoint'], msg: 'invalid url', type: 'value_error' },
        ],
      }),
    }));

    await expect(api.listAgents()).rejects.toThrow('field required; invalid url');
  });
});
