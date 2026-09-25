import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { api } from '../../api';
import { AuthApiKeysPage } from '../../pages/AuthApiKeysPage';

vi.mock('../../api', () => ({
  api: {
    listAuthApiKeys: vi.fn(),
    createAuthApiKey: vi.fn(),
    revokeAuthApiKey: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}));

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listAuthApiKeys).mockResolvedValue({ keys: [] });
  vi.mocked(api.getCurrentUser).mockResolvedValue({ username: 'tester', role: 'admin', scopes: ['admin'] });
});

describe('AuthApiKeysPage', () => {
  it('reads keys through the unified api client instead of raw fetch', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('raw fetch not allowed'));
    render(<AuthApiKeysPage />);
    await waitFor(() => {
      expect(api.listAuthApiKeys).toHaveBeenCalledTimes(1);
    });
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it('creates a key without an owner field and passes scopes and ttl', async () => {
    vi.mocked(api.createAuthApiKey).mockResolvedValue({ id: 'k1', raw_key: 'ae_test' });
    render(<AuthApiKeysPage />);
    fireEvent.click(screen.getByRole('button', { name: /create key/i }));
    fireEvent.click(screen.getByRole('button', { name: /^create$/i }));
    await waitFor(() => {
      expect(api.createAuthApiKey).toHaveBeenCalledTimes(1);
    });
    const payload = vi.mocked(api.createAuthApiKey).mock.calls[0][0];
    expect(payload).not.toHaveProperty('owner');
    expect(payload.scopes).toEqual(expect.arrayContaining(['read', 'write']));
    expect(payload.ttl_days).toBeNull();
  });

  it('restricts scope options for non-admin users', async () => {
    vi.mocked(api.getCurrentUser).mockResolvedValue({ username: 'tester', role: 'user', scopes: ['read', 'write'] });
    render(<AuthApiKeysPage />);
    fireEvent.click(screen.getByRole('button', { name: /create key/i }));
    expect(screen.queryByRole('button', { name: /^read$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^admin$/i })).not.toBeInTheDocument();
  });

  it('revokes a key through the api client', async () => {
    vi.mocked(api.listAuthApiKeys).mockResolvedValue({
      keys: [{
        id: 'k1', name: 'ci', owner: 'tester', scopes: ['read'], is_active: true,
        expires_at: null, last_used_at: null, created_at: null,
      }],
    });
    vi.mocked(api.revokeAuthApiKey).mockResolvedValue({ message: 'ok' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<AuthApiKeysPage />);
    await waitFor(() => {
      expect(screen.getByText('ci')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTitle('Revoke key'));
    await waitFor(() => {
      expect(api.revokeAuthApiKey).toHaveBeenCalledWith('k1');
    });
  });
});
