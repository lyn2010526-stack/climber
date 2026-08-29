import { describe, expect, it, vi } from 'vitest';
import { ApiClient } from './client';

describe('ApiClient retry policy', () => {
  it('does not retry a four hundred response with a detail message', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      {
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Task not found' }),
      },
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(new ApiClient().request('/tasks/missing')).rejects.toThrow('Task not found');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    vi.unstubAllGlobals();
  });

  it('clears cached GET data when the authentication context changes', async () => {
    const tokens = { current: 'user-a-token' };
    const storage = {
      getItem: vi.fn(() => tokens.current),
    };
    vi.stubGlobal('localStorage', storage);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ user: 'a' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ user: 'b' }) });
    vi.stubGlobal('fetch', fetchMock);
    const client = new ApiClient();

    await expect(client.request('/settings')).resolves.toEqual({ user: 'a' });
    tokens.current = 'user-b-token';
    await expect(client.request('/settings')).resolves.toEqual({ user: 'b' });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    vi.unstubAllGlobals();
  });
});
