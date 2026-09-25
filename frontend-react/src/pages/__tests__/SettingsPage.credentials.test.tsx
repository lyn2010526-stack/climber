import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SettingsPage } from '../SettingsPage';

vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }));

const modelKey = {
  id: 'model-test', name: 'Temporary model', provider: 'openai',
  base_url: null, is_active: true, created_at: '2026-09-25T00:00:00Z',
};
const platformKey = {
  id: 'platform-test', name: 'Temporary automation', owner: 'tester',
  scopes: ['read'], is_active: true, expires_at: null, last_used_at: null, created_at: null,
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
let modelKeys: typeof modelKey[];
let platformKeys: typeof platformKey[];
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  modelKeys = [modelKey];
  platformKeys = [platformKey];
  localStorage.clear();
  localStorage.setItem('auth_token', 'temporary-platform-token');
  window.location.hash = '#settings';
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (url, options) => {
    if (url === '/api/v1/auth/me') return json({ username: 'tester', role: 'user', scopes: ['read', 'write'] });
    if (url === '/api/v1/api-keys' && options?.method === 'POST') {
      modelKeys = [...modelKeys, { ...modelKey, id: 'new-model', name: 'Added model' }];
      return json(modelKeys[1]);
    }
    if (url === '/api/v1/api-keys/model-test' && options?.method === 'DELETE') {
      modelKeys = modelKeys.filter(key => key.id !== 'model-test');
      return json({ ok: true });
    }
    if (url === '/api/v1/api-keys') return json(modelKeys);
    if (url === '/api/v1/auth/keys' && options?.method === 'POST') {
      return json({ ...platformKey, id: 'new-platform', raw_key: 'ae_temporary_created' });
    }
    if (url === '/api/v1/auth/keys/platform-test' && options?.method === 'DELETE') {
      platformKeys = [];
      return json({ ok: true });
    }
    if (url === '/api/v1/auth/keys') return json({ keys: platformKeys });
    throw new Error(`Unexpected request: ${String(url)}`);
  });
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  window.location.hash = '';
});

describe('Settings credential entry points', () => {
  it('uses the existing model credential CRUD without requesting platform keys', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('button', { name: /模型凭据/ }));
    expect(await screen.findByText('Temporary model')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '模型凭据' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /copy/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Add Key' }));
    fireEvent.change(screen.getByPlaceholderText('Key name'), { target: { value: 'Added model' } });
    fireEvent.change(screen.getByPlaceholderText('sk-...'), { target: { value: 'sk-temporary-test' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save Key' }));
    expect(await screen.findByText('Added model')).toBeInTheDocument();
    const create = fetchMock.mock.calls.find(([url, options]) => url === '/api/v1/api-keys' && options?.method === 'POST');
    expect(JSON.parse(create![1]!.body as string)).toEqual({
      provider: 'openai', name: 'Added model', api_key: 'sk-temporary-test', base_url: '',
    });
    fireEvent.click(screen.getByRole('button', { name: '删除模型凭据 Temporary model' }));
    await waitFor(() => expect(screen.queryByText('Temporary model')).not.toBeInTheDocument());
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/auth/keys'))).toBe(false);
    expect(localStorage.getItem('auth_token')).toBe('temporary-platform-token');
  });

  it('keeps platform tokens on their own endpoint and retains scope restrictions', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('button', { name: /平台访问令牌/ }));
    expect(await screen.findByText('Temporary automation')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '平台访问令牌' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /create key/i }));
    expect(screen.queryByRole('button', { name: /^admin$/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^create$/i }));
    expect(await screen.findByText('ae_temporary_created')).toBeInTheDocument();
    const create = fetchMock.mock.calls.find(([url, options]) => url === '/api/v1/auth/keys' && options?.method === 'POST');
    expect(JSON.parse(create![1]!.body as string)).toEqual({ name: '', scopes: ['read', 'write'], ttl_days: null });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    fireEvent.click(screen.getByTitle('Revoke key'));
    await waitFor(() => expect(screen.queryByText('Temporary automation')).not.toBeInTheDocument());
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api-keys'))).toBe(false);
  });

  it.each(['模型凭据', '平台访问令牌'])('shows authorization errors in %s without navigating', async (section) => {
    fetchMock.mockResolvedValue(json({ detail: 'Access denied' }, 401));
    render(<SettingsPage />);
    fireEvent.click(screen.getByRole('button', { name: new RegExp(section) }));
    expect(await screen.findByText('Authentication required')).toBeInTheDocument();
    expect(window.location.hash).toBe('#settings');
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/login'))).toBe(false);
  });
});
