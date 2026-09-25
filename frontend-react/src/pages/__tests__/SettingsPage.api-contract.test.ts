import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../api';
import { apiClient, ApiError } from '../../lib/api-client';
import { agentService } from '../../services/agentService';

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  localStorage.clear();
  window.location.hash = '#settings';
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => json([]));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  window.location.hash = '';
});

describe('Settings API contracts', () => {
  it.each(['/api-keys', 'api-keys', '/api/api-keys', '/api/v1/api-keys', 'api/v1/api-keys'])(
    'normalizes %s to exactly one API version prefix', async (path) => {
      await apiClient.get(path);
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/api-keys', expect.any(Object));
    },
  );

  it.each(['/api?limit=1', '/api/v1?limit=1'])(
    'preserves query parameters at the API root: %s', async (path) => {
      await apiClient.get(path);
      expect(fetchMock).toHaveBeenCalledWith('/api/v1?limit=1', expect.any(Object));
    },
  );

  it('uses the same platform bearer token for both clients and streams', async () => {
    localStorage.setItem('auth_token', 'temporary-platform-token');
    localStorage.setItem('climber-auth', JSON.stringify({ state: { token: 'obsolete-token' } }));
    await api.listApiKeys();
    await apiClient.get('/api/api-keys');
    const controller = new AbortController();
    const stream = await apiClient.stream('/api/v1/events', { input: 'test' }, controller.signal);
    expect(stream).toBeInstanceOf(Response);
    for (const [, options] of fetchMock.mock.calls) {
      expect(options?.headers).toMatchObject({ Authorization: 'Bearer temporary-platform-token' });
    }
    expect(fetchMock).toHaveBeenLastCalledWith('/api/v1/events', expect.objectContaining({
      signal: controller.signal, body: JSON.stringify({ input: 'test' }),
    }));
  });

  it('preserves skipAuth, custom headers, abort signal, and service response shape', async () => {
    localStorage.setItem('auth_token', 'temporary-platform-token');
    const controller = new AbortController();
    await apiClient.post('/api/api-keys', { name: 'temporary' }, {
      skipAuth: true, headers: { 'X-Test': 'temporary' }, signal: controller.signal,
    });
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST', headers: { 'X-Test': 'temporary' }, signal: controller.signal,
      body: JSON.stringify({ name: 'temporary' }),
    });
    expect(fetchMock.mock.calls[0][1]?.headers).not.toHaveProperty('Authorization');
    fetchMock.mockResolvedValueOnce(json([{ id: 'temporary-agent' }]));
    await expect(agentService.list()).resolves.toEqual([{ id: 'temporary-agent' }]);
    expect(fetchMock).toHaveBeenLastCalledWith('/api/v1/agents', expect.any(Object));
  });

  it.each(['get', 'post', 'put', 'patch', 'delete'] as const)('preserves the %s service method', async (method) => {
    await apiClient[method]('/api/api-keys');
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/api-keys', expect.objectContaining({ method: method.toUpperCase() }));
  });

  it('allows requests when browser storage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Storage unavailable'); });
    await expect(api.listApiKeys()).resolves.toEqual([]);
    await expect(apiClient.get('/api/api-keys')).resolves.toEqual([]);
    for (const [, options] of fetchMock.mock.calls) expect(options?.headers).not.toHaveProperty('Authorization');
  });

  it('keeps both clients on the current page after 401', async () => {
    fetchMock.mockImplementation(async () => json({ detail: 'Token expired' }, 401));
    await expect(api.listApiKeys()).rejects.toThrow('Authentication required');
    await expect(apiClient.get('/api/api-keys')).rejects.toMatchObject({ status: 401, data: { detail: 'Token expired' } });
    expect(window.location.hash).toBe('#settings');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('preserves structured errors for non-JSON 401 responses', async () => {
    fetchMock.mockResolvedValueOnce(new Response('Token expired', { status: 401 }));
    const error = await apiClient.get('/api/api-keys').catch(error => error);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401, data: 'Token expired' });
    expect(window.location.hash).toBe('#settings');
  });

  it('preserves the existing refresh-token contract and retries once', async () => {
    localStorage.setItem('auth_token', 'expired-token');
    localStorage.setItem('refresh_token', 'temporary-refresh');
    fetchMock.mockResolvedValueOnce(json({ detail: 'Expired' }, 401));
    fetchMock.mockResolvedValueOnce(json({ access_token: 'renewed-token' }));
    fetchMock.mockResolvedValueOnce(json([]));
    await expect(api.listApiKeys()).resolves.toEqual([]);
    expect(fetchMock.mock.calls[1]).toEqual(['/api/v1/auth/refresh', expect.objectContaining({
      body: JSON.stringify({ refresh_token: 'temporary-refresh' }),
    })]);
    expect(fetchMock.mock.calls[2][1]?.headers).toMatchObject({ Authorization: 'Bearer renewed-token' });
    expect(localStorage.getItem('auth_token')).toBe('renewed-token');
    expect(window.location.hash).toBe('#settings');
  });

  it.each([undefined, { prompt: 'temporary input' }])('wraps workflow input as the backend schema requires: %j', async (inputs) => {
    await api.runWorkflow('temporary-workflow', inputs);
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/workflows/temporary-workflow/run', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ inputs: inputs || {} }),
    }));
  });
});
