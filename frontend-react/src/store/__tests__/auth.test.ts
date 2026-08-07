import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../auth';

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

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      loading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it('has initial unauthenticated state', () => {
    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('setToken sets token and authentication', () => {
    useAuthStore.getState().setToken('test-token');
    expect(useAuthStore.getState().token).toBe('test-token');
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('setUser sets user', () => {
    const user = { id: '1', name: 'Test', email: 'test@test.com', role: 'user' };
    useAuthStore.getState().setUser(user);
    expect(useAuthStore.getState().user).toEqual(user);
  });

  it('login sets token, user and authenticated', async () => {
    const user = { id: '1', name: 'Test', email: 'test@test.com', role: 'user' };
    (apiClient.post as any).mockResolvedValue({
      access_token: 'token-123',
      refresh_token: 'refresh-456',
      token_type: 'bearer',
      user: { id: '1', username: 'Test', email: 'test@test.com', role: 'user' },
    });

    await useAuthStore.getState().login('testuser', 'password123');
    expect(useAuthStore.getState().token).toBe('token-123');
    expect(useAuthStore.getState().user).toEqual(user);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it('logout clears all state', async () => {
    const user = { id: '1', name: 'Test', email: 'test@test.com', role: 'user' };
    (apiClient.post as any).mockResolvedValue({
      access_token: 'token-123',
      refresh_token: 'refresh-456',
      token_type: 'bearer',
      user: { id: '1', username: 'Test', email: 'test@test.com', role: 'user' },
    });
    await useAuthStore.getState().login('testuser', 'password123');
    (apiClient.post as any).mockResolvedValue({});
    await useAuthStore.getState().logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it('setToken with null clears authentication', () => {
    useAuthStore.getState().setToken('token');
    useAuthStore.getState().setToken(null);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
