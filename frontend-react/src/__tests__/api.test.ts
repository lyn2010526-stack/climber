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
  it('loads workflow node metadata and runs one node', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [{ type: 'code', label: 'Code', inputs: [], outputs: [] }],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ node_id: 'code-1', status: 'completed', output: {}, error: '' }),
      });
    vi.stubGlobal('fetch', fetchMock);

    await expect(api.getWorkflowNodeTypes()).resolves.toEqual([
      { type: 'code', label: 'Code', inputs: [], outputs: [] },
    ]);
    await api.runWorkflowNode({ id: 'code-1', type: 'code', data: {} }, { value: 'hello' });

    expect(fetchMock).toHaveBeenLastCalledWith(
      '/api/v1/workflows/nodes/run',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          node: { id: 'code-1', type: 'code', data: {} },
          inputs: { value: 'hello' },
        }),
      }),
    );
  });

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

  it('sends concurrent permission mutations independently', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'resolved' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await Promise.all([
      api.resolvePermission('approval-1', 'allow'),
      api.resolvePermission('approval-2', 'deny'),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls.map(([, options]) => options.body)).toEqual([
      JSON.stringify({ tool_call_id: 'approval-1', decision: 'allow' }),
      JSON.stringify({ tool_call_id: 'approval-2', decision: 'deny' }),
    ]);
  });
});
